"""Unit tests for game_log_reader: parsing, classification, mod-only filter,
dedup, diff, session clustering, and category summarization.
"""
import os
import tempfile
import time
import unittest
from unittest import mock

import game_log_reader
from game_log_reader import (
    parse_log,
    LogEntry,
    LogFileInfo,
    list_logs,
    filter_mod_only,
    filter_debug_log,
    filter_entries,
    dedupe,
    diff_against_backup,
    cluster_sessions,
    summarize,
    render_error_log_digest,
    MESSAGE_CATEGORY_BY_FILE,
    SOURCE_CATEGORY_FILE,
    SOURCE_CATEGORY_PREFIX,
    load_vanilla_bug_registry,
    load_mod_noise_registry,
    tag_vanilla_bugs,
    _github_slug,
    _open_issues_anchors,
    _vanilla_bug_cache,
    GUI_INJECTED_SCOPE_REF,
    gui_injected_scope_names,
    tag_gui_injected_scopes,
    helper_anchor_warnings,
    mod_frame_test,
    mod_only_anchor_warnings,
    mod_uses,
    apply_known_noise_modes,
    WATCH_KIND,
    MOD_GUI_UNTAG_NO_INSTALL,
    MOD_GUI_UNTAG_NO_VANILLA_LOC,
    mod_gui_references,
    new_mod_gui_warnings,
    untag_mod_gui_fetches,
    vanilla_gui_file_names,
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

    def test_parses_the_1_15_gamedatabase_lines(self):
        # error.log, vanilla 1.15.0, 2026-11-10 (#1571): the same two messages
        # 1.14.5 logged from gamedatabase.h:378 and :395.
        path = _write_log(
            "[10:21:16][gamedatabase.h:394]: Duplicated key has_indian_primary_culture will not be "
            "created from file: common/scripted_triggers/00_scripted_triggers.txt:2015\n"
            "[10:21:18][gamedatabase.h:411]: You are trying to inject/replace to a non-existing entry: "
            "te_probe_pic_no_such_terrain:Inject in the file common/terrain/te_probe_pics_c.txt:2\n"
        )
        try:
            entries = parse_log(path)
        finally:
            os.remove(path)
        self.assertEqual([e.source for e in entries], ["gamedatabase.h:394", "gamedatabase.h:411"])
        self.assertEqual([e.category for e in entries], ["duplicated_key", "inject_to_missing"])
        self.assertEqual(entries[1].files, ["common/terrain/te_probe_pics_c.txt"])

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

    DUPLICATED_KEY = ("Duplicated key has_indian_primary_culture will not be created from file: "
                      "common/scripted_triggers/00_scripted_triggers.txt:2015")
    INJECT_TO_MISSING = ("You are trying to inject/replace to a non-existing entry: "
                         "te_probe_pic_no_such_terrain:Inject in the file common/terrain/te_probe_pics_c.txt:2")

    def test_gamedatabase_lines_classify_on_1_14_and_1_15(self):
        # 1.15.0 moved both lines by 16 (#1571): 378 -> 394, 395 -> 411.
        for source in ("gamedatabase.h:378", "gamedatabase.h:394"):
            with self.subTest(source=source):
                self.assertEqual(LogEntry("00:00:00", source, self.DUPLICATED_KEY).category, "duplicated_key")
        for source in ("gamedatabase.h:395", "gamedatabase.h:411"):
            with self.subTest(source=source):
                self.assertEqual(LogEntry("00:00:00", source, self.INJECT_TO_MISSING).category,
                                 "inject_to_missing")

    def test_gamedatabase_lines_classify_by_message_at_an_unknown_line(self):
        # The next patch moves the lines again: the message text still says
        # which of the two it is, so neither drops to gamedatabase_other.
        for source in ("gamedatabase.h:427", "gamedatabase.h:1", "gamedatabase.h"):
            with self.subTest(source=source):
                self.assertEqual(LogEntry("00:00:00", source, self.DUPLICATED_KEY).category, "duplicated_key")
                self.assertEqual(LogEntry("00:00:00", source, self.INJECT_TO_MISSING).category,
                                 "inject_to_missing")

    def test_gamedatabase_message_outranks_a_line_number_another_version_used(self):
        # One version's line number can be another version's line for the
        # other message; the text is what the engine said.
        sources = [k for k in SOURCE_CATEGORY_PREFIX if k.startswith("gamedatabase.h:")]
        self.assertTrue(sources)
        for source in sources:
            with self.subTest(source=source):
                self.assertEqual(LogEntry("00:00:00", source, self.DUPLICATED_KEY).category,
                                 "duplicated_key")
                self.assertEqual(LogEntry("00:00:00", source, self.INJECT_TO_MISSING).category,
                                 "inject_to_missing")

    def test_gamedatabase_known_line_with_new_wording_keeps_its_category(self):
        # The other way round: the wording changes and the line stays.
        for source, category in (("gamedatabase.h:378", "duplicated_key"),
                                 ("gamedatabase.h:394", "duplicated_key"),
                                 ("gamedatabase.h:395", "inject_to_missing"),
                                 ("gamedatabase.h:411", "inject_to_missing")):
            with self.subTest(source=source):
                self.assertEqual(LogEntry("00:00:00", source, "reworded").category, category)

    def test_other_gamedatabase_lines_stay_gamedatabase_other(self):
        e = LogEntry("00:00:00", "gamedatabase.h:500", "Some other database complaint")
        self.assertEqual(e.category, "gamedatabase_other")
        # The text only counts at the start of the message.
        e = LogEntry("00:00:00", "gamedatabase.h:500", "Entry x: Duplicated key y")
        self.assertEqual(e.category, "gamedatabase_other")

    def test_gamedatabase_message_rules_cover_no_other_source(self):
        # `Duplicated key` in another file's message (a script's debug_log
        # line, say) is not the database's dropped duplicate.
        e = LogEntry("00:00:00", "jomini_effect_impl.cpp:454", "Duplicated key foo")
        self.assertEqual(e.category, "debug_log")
        e = LogEntry("00:00:00", "completely_made_up.cpp:99", self.INJECT_TO_MISSING)
        self.assertEqual(e.category, "other")

    def test_message_category_rules_name_files_the_file_table_knows(self):
        # A message rule refines a file's category, so its file needs the
        # whole-file fallback too, and is keyed without a `:line`.
        for source_file, rules in MESSAGE_CATEGORY_BY_FILE.items():
            with self.subTest(source_file=source_file):
                self.assertIn(source_file, SOURCE_CATEGORY_FILE)
                self.assertNotIn(":", source_file)
                self.assertTrue(all(prefix and category for prefix, category in rules))

    def test_unknown_source_falls_back_to_other(self):
        e = LogEntry("00:00:00", "completely_made_up.cpp:99", "whatever")
        self.assertEqual(e.category, "other")

    def test_file_part_match_when_specific_line_unknown(self):
        # `pdx_gui_factory.cpp:611` and `:909` aren't in the prefix table but
        # the file-only mapping should catch them.
        e = LogEntry("00:00:00", "pdx_gui_factory.cpp:909", "X is not a valid type")
        self.assertEqual(e.category, "gui_parse_error")

    def test_physfs_lines_are_vfs_mount_not_other(self):
        # #254 §6: the rule lived in SOURCE_CATEGORY_PREFIX as
        # "virtualfilesystem_physfs.cpp:" — a key `_classify` could never match,
        # since it compares whole `file:line` sources. Any line of that file is
        # a mount complaint.
        for source in ("virtualfilesystem_physfs.cpp:213",
                       "virtualfilesystem_physfs.cpp:57",
                       "virtualfilesystem_physfs.cpp"):
            with self.subTest(source=source):
                e = LogEntry("00:00:00", source, "Could not mount ...")
                self.assertEqual(e.category, "vfs_mount")

    def test_debug_log_output_is_its_own_category(self):
        # Script debug_log lines (:454 today, :453 before 1.14) and the
        # debug_log_scopes dump (:2501) are trace output, not errors.
        for source, message in (
            ("jomini_effect_impl.cpp:454", "common/scripted_effects/gm_effects.txt:1194: TE_MONUMENTS: 10 monuments"),
            ("jomini_effect_impl.cpp:453", " file: common/on_actions/00_code_on_actions.txt line: 4785: Fascist Party Created"),
            ("jomini_effect_impl.cpp:2501", "State Trucial Coast (x505AE0)\nRoot: Country Byzantium (88)"),
        ):
            with self.subTest(source=source):
                self.assertEqual(LogEntry("00:00:00", source, message).category, "debug_log")

    def test_never_set_validator_is_not_a_scope_error(self):
        e = LogEntry("00:00:00", "jomini_effect.cpp:1139",
                     "Variable 'sr_active_milestone' is used but is never set.")
        self.assertEqual(e.category, "used_but_never_set")
        # Other lines of the file keep the file-level rule.
        e = LogEntry("00:00:00", "jomini_effect.cpp:760", "Inconsistent effect scopes")
        self.assertEqual(e.category, "inconsistent_effect_scope")

    def test_no_dead_prefix_keys(self):
        # A `"<file>:"` key in the exact-match table is unreachable; whole-file
        # rules belong in SOURCE_CATEGORY_FILE. (#254 §6)
        dead = [k for k in SOURCE_CATEGORY_PREFIX if not k.rpartition(":")[2].isdigit()]
        self.assertEqual(dead, [])


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

    def test_filter_debug_log_modes(self):
        trace = LogEntry("00:00:00", "jomini_effect_impl.cpp:454", "common/scripted_effects/x.txt:1: TE_X: hello")
        dump = LogEntry("00:00:00", "jomini_effect_impl.cpp:2501", "State X (x1)\nRoot: Country Y (2)")
        error = LogEntry("00:00:00", "gamedatabase.h:378", "Duplicated key concept_x")
        entries = [trace, error, dump]
        self.assertEqual(filter_debug_log(entries, "hide"), [error])
        self.assertEqual(filter_debug_log(entries, "only"), [trace, dump])
        self.assertEqual(filter_debug_log(entries, "show"), entries)
        self.assertEqual(filter_debug_log(entries, "bogus"), entries)

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


class VanillaBugRegistryTests(unittest.TestCase):
    """Cover the source-anchored / mod_low_priority / cross-reference-validation
    behavior added to load_vanilla_bug_registry + tag_vanilla_bugs.
    """

    def _write_doc(self, dirpath: str, content: str) -> str:
        # Mirrors the live layout: registry lives under docs/vanilla/.
        sub = os.path.join(dirpath, "vanilla")
        os.makedirs(sub, exist_ok=True)
        path = os.path.join(sub, "vanilla_known_bugs.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        # Bust the in-process mtime cache so each test gets a fresh parse.
        _vanilla_bug_cache.clear()
        return path

    def _write_mod_noise_doc(self, dirpath: str, content: str) -> str:
        # Mirrors docs/audits/mod_known_noise.md.
        sub = os.path.join(dirpath, "audits")
        os.makedirs(sub, exist_ok=True)
        path = os.path.join(sub, "mod_known_noise.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        _vanilla_bug_cache.clear()
        return path

    def _write_open_issues(self, dirpath: str, content: str) -> str:
        sub = os.path.join(dirpath, "audits")
        os.makedirs(sub, exist_ok=True)
        path = os.path.join(sub, "open_issues.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_path_anchored_legacy_entry_still_works(self):
        """Regression: a normal `### `path/to/file.txt`` entry tags entries
        whose `files` contains the basename. No source/kind/tracked needed."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "")
            doc = self._write_doc(tmp, """
## Script errors observed

### `common/treaty_articles/foo.txt:54` — vanilla scope bug

```
Error: Event target link 'scope' returned an invalid object
```
""")
            refs, by_basename, by_source, warnings = load_vanilla_bug_registry(doc)
            self.assertEqual(len(refs), 1)
            self.assertEqual(warnings, [])
            self.assertIn("foo.txt", by_basename)
            self.assertEqual(by_source, {})
            entry = LogEntry(
                time="00:00:01",
                source="jomini_script_system.cpp:247",
                message="Script system error!\n  Error: Event target link 'scope' returned an invalid object\n  Script location: common/treaty_articles/foo.txt:54",
            )
            tag_vanilla_bugs([entry], by_basename, by_source)
            self.assertIsNotNone(entry.vanilla_bug_ref)
            self.assertEqual(entry.vanilla_bug_ref["kind"], "vanilla")

    def test_source_anchored_tags_entry_with_empty_files(self):
        """A `- source:` ref tags entries whose .files is empty but whose
        .source matches. This is the new path-less filter mechanism."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "")
            doc = self._write_doc(tmp, """
## Engine noise (source-anchored)

### `building_manager.cpp:1792` — vanilla auto-charter duplicate building seeding
- source: `building_manager.cpp:1792`

```
Tried to create building of Type building_company_basic_
```
""")
            refs, by_basename, by_source, warnings = load_vanilla_bug_registry(doc)
            self.assertEqual(warnings, [])
            self.assertEqual(by_basename, {})
            self.assertIn("building_manager.cpp:1792", by_source)
            entry = LogEntry(
                time="00:00:01",
                source="building_manager.cpp:1792",
                message="Tried to create building of Type building_company_basic_fabrics in State 'Foo'",
            )
            self.assertEqual(entry.files, [])
            tag_vanilla_bugs([entry], by_basename, by_source)
            self.assertIsNotNone(entry.vanilla_bug_ref)
            self.assertEqual(entry.vanilla_bug_ref["kind"], "vanilla_noise")

    def test_source_anchored_signature_narrows_match(self):
        """Different message at the same source must NOT be tagged. Anchor
        narrows scope but the signature substring narrows it further."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "")
            doc = self._write_doc(tmp, """
## Engine noise (source-anchored)

### `building_manager.cpp:1792` — duplicate building seeding only
- source: `building_manager.cpp:1792`

```
Tried to create building of Type building_company_basic_
```
""")
            _, by_basename, by_source, _ = load_vanilla_bug_registry(doc)
            unrelated = LogEntry(
                time="00:00:01",
                source="building_manager.cpp:1792",
                message="Some completely unrelated future error from this cpp:line",
            )
            tag_vanilla_bugs([unrelated], by_basename, by_source)
            self.assertIsNone(unrelated.vanilla_bug_ref)

    def test_anchor_less_ref_rejected(self):
        """A ref with no path AND no source is rejected at parse time + warns."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "")
            doc = self._write_doc(tmp, """
## Script errors observed

### Some title with no anchor at all

```
some message substring
```
""")
            refs, _, _, warnings = load_vanilla_bug_registry(doc)
            self.assertEqual(refs, [])
            self.assertTrue(any("no file path or source anchor" in w for w in warnings))

    def test_mod_low_priority_requires_tracked_issue(self):
        """A ref under `## Mod-side ...` without `- tracked:` is rejected via warning."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "## LOW\n\n### L7. existing\n")
            doc = self._write_doc(tmp, """
## Mod-side cosmetic, tracked-not-fixed (source-anchored)

### `harvest_condition_graphics.cpp:52` — missing sound states
- source: `harvest_condition_graphics.cpp:52`

```
Couldn't find any animation state for harvest condition type
```
""")
            refs, _, _, warnings = load_vanilla_bug_registry(doc)
            # Ref still loads (it has a source anchor) but a warning fires.
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0].kind, "mod_low_priority")
            self.assertTrue(any("tracked" in w.lower() for w in warnings))

    def test_mod_low_priority_unresolved_anchor_warns(self):
        """A `- tracked:` link whose #anchor doesn't resolve in open_issues.md warns."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "## LOW\n\n### L7. real anchor\n")
            doc = self._write_doc(tmp, """
## Mod-side cosmetic, tracked-not-fixed (source-anchored)

### `harvest_condition_graphics.cpp:52` — missing sound states
- source: `harvest_condition_graphics.cpp:52`
- tracked: `docs/audits/open_issues.md#l99-does-not-exist`

```
Couldn't find any animation state for harvest condition type
```
""")
            _, _, _, warnings = load_vanilla_bug_registry(doc)
            self.assertTrue(any("does not resolve" in w for w in warnings))

    def test_unresolved_anchor_suggests_nearest_and_slug_rule(self):
        """A near-miss anchor gets a `Did you mean:` suggestion for the closest
        real anchor plus the copy-paste slug rule — while preserving the
        `does not resolve` phrase the older assertion depends on."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(
                tmp, "## LOW\n\n### L7. mod harvest condition sound entity states missing\n")
            doc = self._write_doc(tmp, """
## Mod-side cosmetic, tracked-not-fixed (source-anchored)

### `harvest_condition_graphics.cpp:52` — missing sound states
- source: `harvest_condition_graphics.cpp:52`
- tracked: `docs/audits/open_issues.md#l7-mod-harvest-conditon-sound`

```
Couldn't find any animation state for harvest condition type
```
""")
            _, _, _, warnings = load_vanilla_bug_registry(doc)
            joined = "\n".join(warnings)
            self.assertIn("does not resolve", joined)
            self.assertIn("Did you mean", joined)
            self.assertIn("#l7-mod-harvest-condition-sound-entity-states-missing", joined)
            self.assertIn("Anchor rule", joined)

    def test_mod_low_priority_resolved_anchor_clean(self):
        """A `- tracked:` link whose #anchor resolves produces no warning."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "## LOW\n\n### L7. mod harvest condition sound entity states missing\n\nFix it eventually.\n")
            doc = self._write_doc(tmp, """
## Mod-side cosmetic, tracked-not-fixed (source-anchored)

### `harvest_condition_graphics.cpp:52` — missing sound states
- source: `harvest_condition_graphics.cpp:52`
- tracked: `docs/audits/open_issues.md#l7-mod-harvest-condition-sound-entity-states-missing`

```
Couldn't find any animation state for harvest condition type
```
""")
            refs, _, _, warnings = load_vanilla_bug_registry(doc)
            self.assertEqual(warnings, [])
            self.assertEqual(refs[0].tracked_issue, "docs/audits/open_issues.md#l7-mod-harvest-condition-sound-entity-states-missing")
            self.assertEqual(refs[0].to_dict()["tracked_issue"], "docs/audits/open_issues.md#l7-mod-harvest-condition-sound-entity-states-missing")

    def test_mod_noise_registry_loads_with_default_kind(self):
        """`load_mod_noise_registry` defaults entries to mod_low_priority kind
        even when their section header doesn't say `## Mod-side`."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "## LOW\n\n### L7. mod harvest condition sound entity states missing\n")
            doc = self._write_mod_noise_doc(tmp, """# Mod Known Noise

### `harvest_condition_graphics.cpp:52` — missing sound states
- source: `harvest_condition_graphics.cpp:52`
- tracked: `docs/audits/open_issues.md#l7-mod-harvest-condition-sound-entity-states-missing`

```
Couldn't find any animation state for harvest condition type
```
""")
            refs, by_basename, by_source, warnings = load_mod_noise_registry(doc)
            self.assertEqual(warnings, [])
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0].kind, "mod_low_priority")
            entry = LogEntry(
                time="00:00:01",
                source="harvest_condition_graphics.cpp:52",
                message="Couldn't find any animation state for harvest condition type 'bull_market'",
            )
            tag_vanilla_bugs([entry], by_basename, by_source)
            self.assertIsNotNone(entry.vanilla_bug_ref)
            self.assertEqual(entry.vanilla_bug_ref["kind"], "mod_low_priority")
            self.assertIn("tracked_issue", entry.vanilla_bug_ref)

    def test_two_pass_tagging_does_not_overwrite(self):
        """Calling tag_vanilla_bugs twice (once per registry) must not let the
        second pass overwrite a match found by the first pass."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "## LOW\n\n### L7. mod harvest condition sound entity states missing\n")
            # Registry 1: vanilla — matches by source
            v_doc = self._write_doc(tmp, """
## Engine noise (source-anchored)

### `shared.cpp:1` — vanilla noise
- source: `shared.cpp:1`

```
shared signature
```
""")
            _, vb_basenames, vb_sources, _ = load_vanilla_bug_registry(v_doc)
            # Registry 2: mod_noise — would also match by source if first pass didn't tag
            mn_doc = self._write_mod_noise_doc(tmp, """# Mod Known Noise

### `shared.cpp:1` — mod cosmetic
- source: `shared.cpp:1`
- tracked: `docs/audits/open_issues.md#l7-mod-harvest-condition-sound-entity-states-missing`

```
shared signature
```
""")
            _, mn_basenames, mn_sources, _ = load_mod_noise_registry(mn_doc)
            entry = LogEntry(
                time="00:00:01",
                source="shared.cpp:1",
                message="shared signature in body",
            )
            # Pass 1: vanilla registry tags it as vanilla_noise
            tag_vanilla_bugs([entry], vb_basenames, vb_sources)
            self.assertEqual(entry.vanilla_bug_ref["kind"], "vanilla_noise")
            # Pass 2: mod_noise registry should leave the prior tag alone
            tag_vanilla_bugs([entry], mn_basenames, mn_sources)
            self.assertEqual(entry.vanilla_bug_ref["kind"], "vanilla_noise")

    def test_path_anchored_wins_over_source_anchored(self):
        """When an entry has both a matching basename AND a matching source,
        the path-anchored ref is selected first (legacy compatibility)."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_open_issues(tmp, "")
            doc = self._write_doc(tmp, """
## Script errors observed

### `common/foo.txt:1` — path-anchored

```
shared signature substring here
```

## Engine noise (source-anchored)

### `some.cpp:1` — source-anchored fallback
- source: `some.cpp:1`

```
shared signature substring here
```
""")
            _, by_basename, by_source, _ = load_vanilla_bug_registry(doc)
            entry = LogEntry(
                time="00:00:01",
                source="some.cpp:1",
                message="shared signature substring here at common/foo.txt:1",
            )
            tag_vanilla_bugs([entry], by_basename, by_source)
            self.assertIsNotNone(entry.vanilla_bug_ref)
            self.assertEqual(entry.vanilla_bug_ref["kind"], "vanilla")  # path-anchored, default kind


class StackVanillaOnlyTests(unittest.TestCase):
    """`- stack: vanilla only` (#863) and the bare-path signature warning (#873)."""

    STACK = (
        "Script system error!\n  Error: Event target link 'capital' returned an unset scope\n"
        "  Script location: common/scripted_triggers/00_scripted_triggers.txt:1065 <- {frames}"
        "common/ai_strategies/00_default_strategy.txt:6513"
    )

    def _registry(self, tmp: str, extra_lines: str = "") -> str:
        os.makedirs(os.path.join(tmp, "docs", "audits"), exist_ok=True)
        with open(os.path.join(tmp, "docs", "audits", "open_issues.md"), "w", encoding="utf-8") as f:
            f.write("")
        os.makedirs(os.path.join(tmp, "docs", "vanilla"), exist_ok=True)
        path = os.path.join(tmp, "docs", "vanilla", "vanilla_known_bugs.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "## Script errors observed\n\n"
                "### `common/ai_strategies/00_default_strategy.txt` — AI reads a stateless capital\n"
                f"{extra_lines}\n"
                "```\nEvent target link 'capital' returned an unset scope\n```\n"
            )
        _vanilla_bug_cache.clear()
        return path

    def _mod(self, tmp: str) -> str:
        mod = os.path.join(tmp, "mod")
        os.makedirs(os.path.join(mod, "common", "on_actions"))
        with open(os.path.join(mod, "common", "on_actions", "un_on_actions.txt"), "w", encoding="utf-8") as f:
            f.write("")
        return mod

    def _entries(self):
        engine_only = LogEntry("00:00:01", "jomini_script_system.cpp:304", self.STACK.format(frames=""))
        mod_caused = LogEntry("00:00:02", "jomini_script_system.cpp:304", self.STACK.format(
            frames="common/on_actions/un_on_actions.txt:88 <- "))
        return engine_only, mod_caused

    def test_vanilla_only_stack_is_tagged_and_a_mod_frame_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, by_basename, by_source, warnings = load_vanilla_bug_registry(
                self._registry(tmp, "- stack: vanilla only\n"))
            self.assertEqual(warnings, [])
            self.assertTrue(refs[0].vanilla_stack_only)
            engine_only, mod_caused = self._entries()
            self.assertIn("common/on_actions/un_on_actions.txt", mod_caused.files)
            tag_vanilla_bugs([engine_only, mod_caused], by_basename, by_source, mod_root=self._mod(tmp))
            self.assertEqual(engine_only.vanilla_bug_ref["stack"], "vanilla only")
            self.assertIsNone(mod_caused.vanilla_bug_ref)

    def test_without_the_line_both_are_tagged_as_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, by_basename, by_source, _ = load_vanilla_bug_registry(self._registry(tmp))
            self.assertFalse(refs[0].vanilla_stack_only)
            engine_only, mod_caused = self._entries()
            tag_vanilla_bugs([engine_only, mod_caused], by_basename, by_source, mod_root=self._mod(tmp))
            self.assertIsNotNone(engine_only.vanilla_bug_ref)
            self.assertIsNotNone(mod_caused.vanilla_bug_ref)
            self.assertNotIn("stack", engine_only.vanilla_bug_ref)

    def test_without_a_mod_root_a_vanilla_only_entry_tags_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, by_basename, by_source, _ = load_vanilla_bug_registry(
                self._registry(tmp, "- stack: vanilla only\n"))
            engine_only, mod_caused = self._entries()
            tag_vanilla_bugs([engine_only, mod_caused], by_basename, by_source)
            self.assertIsNone(engine_only.vanilla_bug_ref)
            self.assertIsNone(mod_caused.vanilla_bug_ref)

    def test_unknown_stack_value_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, _, _, warnings = load_vanilla_bug_registry(self._registry(tmp, "- stack: engine\n"))
            self.assertFalse(refs[0].vanilla_stack_only)
            self.assertEqual(len(warnings), 1)
            self.assertIn("- stack: vanilla only", warnings[0])

    def test_bare_path_signatures_warn_and_message_text_does_not(self):
        bare = [
            "common/ai_strategies/00_default_strategy.txt:2382",
            "00_default_strategy.txt:2382",
            "royal_wedding.txt:112",
            "Script location: common/script_values/00_infamy_values.txt",
            "common/journal_entries/00_east_indies.txt",
            "`gui/companies_panel.gui:1`",
        ]
        fine = [
            "Div/0 near common/treaty_articles/05_transfer_money.txt:149",
            "Value of wrong type in 'common/script_values/command_values.txt:373'. Got value of type 'none'",
            "Event target link 'capital' returned an unset scope",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = self._registry(tmp)
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n### `common/foo.txt` — mixed signatures\n\n```\n"
                        + "\n".join(bare + fine) + "\n```\n")
            _vanilla_bug_cache.clear()
            _, _, _, warnings = load_vanilla_bug_registry(path)
        flagged = [w for w in warnings if "is only a file path" in w]
        self.assertEqual(len(flagged), len(bare))
        for sig in bare:
            self.assertTrue(any(f"`{sig}`" in w for w in flagged), sig)

    def test_entry_with_no_signature_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._registry(tmp)
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n### `common/foo.txt` — no block\n\nProse only.\n")
            _vanilla_bug_cache.clear()
            _, _, _, warnings = load_vanilla_bug_registry(path)
        self.assertEqual(len([w for w in warnings if "has no signature" in w]), 1)

    def test_sibling_that_can_match_a_stack_only_message_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._registry(tmp, "- stack: vanilla only\n")
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n### `common/ai_strategies/00_default_strategy.txt:5065` — sibling\n\n"
                        "```\nError: Event target link 'capital' returned an unset scope\n```\n"
                        "\n### `common/ai_strategies/00_default_strategy.txt:7` — unrelated\n\n"
                        "```\nSomething else entirely\n```\n")
            _vanilla_bug_cache.clear()
            _, _, _, warnings = load_vanilla_bug_registry(path)
        shadow = [w for w in warnings if "can match the same message" in w]
        self.assertEqual(len(shadow), 1)
        self.assertIn("'sibling'", shadow[0])

    def test_mod_frame_with_a_leading_slash_still_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = self._mod(tmp)
            self.assertTrue(mod_frame_test(mod)(["/common/on_actions/un_on_actions.txt"]))

    def test_live_mod_noise_registry_is_warning_free(self):
        root = os.path.dirname(os.path.abspath(__file__))
        _vanilla_bug_cache.clear()
        _, _, _, warnings = load_mod_noise_registry(os.path.join(root, "docs", "audits", "mod_known_noise.md"))
        self.assertEqual(warnings, [])


class LiveGamedatabaseNoiseTests(unittest.TestCase):
    """The culture merges' restated `has_indian_primary_culture` drops vanilla's
    copy at every launch (open_issues.md L31). A registry `- source:` matches an
    entry's `file:line` exactly, so the entry lists the line of each vanilla
    version: 1.15.0 logs it from gamedatabase.h:394, 1.14.5 from :378 (#1571)."""

    MESSAGE = ("Duplicated key has_indian_primary_culture will not be created from file: "
               "common/scripted_triggers/00_scripted_triggers.txt:2015")

    def _tag(self, source: str, message: str) -> LogEntry:
        root = os.path.dirname(os.path.abspath(__file__))
        _vanilla_bug_cache.clear()
        _, by_basename, by_source, _ = load_mod_noise_registry(
            os.path.join(root, "docs", "audits", "mod_known_noise.md"))
        entry = LogEntry("10:21:16", source, message)
        tag_vanilla_bugs([entry], by_basename, by_source, mod_root=root)
        return entry

    def test_the_restated_trigger_line_is_tagged_on_1_14_and_1_15(self):
        for source in ("gamedatabase.h:378", "gamedatabase.h:394"):
            with self.subTest(source=source):
                entry = self._tag(source, self.MESSAGE)
                self.assertIsNotNone(entry.vanilla_bug_ref)
                self.assertEqual(entry.vanilla_bug_ref["kind"], "mod_low_priority")
                self.assertIn("culture merges", entry.vanilla_bug_ref["title"])

    def test_a_line_naming_the_mods_copy_is_not_tagged(self):
        # The signature names vanilla's file on purpose: the mod's file in
        # that place means the mod's copy lost.
        message = ("Duplicated key has_indian_primary_culture will not be created from file: "
                   "common/scripted_triggers/00_a_te_culture_merge_vanilla_triggers.txt:9")
        for source in ("gamedatabase.h:378", "gamedatabase.h:394"):
            with self.subTest(source=source):
                self.assertIsNone(self._tag(source, message).vanilla_bug_ref)


class GitHubHeadingSlugTests(unittest.TestCase):
    """`_github_slug` must reproduce GitHub's heading-anchor rule exactly —
    a self-consistent but wrong rule made broken `- tracked:` links validate."""

    def test_punctuation_is_deleted_not_collapsed(self):
        """`_` survives; `.`, `:`, backticks and parens vanish outright (they are
        NOT turned into dashes, which is what the old rule did)."""
        self.assertEqual(
            _github_slug("L16. Historical law seeding vs `unlocking_technologies` "
                         "retention warnings (1.13.9+)"),
            "l16-historical-law-seeding-vs-unlocking_technologies-retention-warnings-1139",
        )
        self.assertEqual(
            _github_slug("L8. Mod tooltip.gui vertical scrollbar template warning"),
            "l8-mod-tooltipgui-vertical-scrollbar-template-warning",
        )
        self.assertEqual(
            _github_slug("L15. Vanilla principles orphaned by REPLACE:principle_group overrides"),
            "l15-vanilla-principles-orphaned-by-replaceprinciple_group-overrides",
        )

    def test_spaces_around_removed_chars_leave_double_dashes(self):
        """An em dash between spaces is deleted, leaving both spaces -> `--`."""
        self.assertEqual(_github_slug("Pending verification gate — RESOLVED 2026-07-03"),
                         "pending-verification-gate--resolved-2026-07-03")

    def test_duplicate_headings_get_numeric_suffix(self):
        """GitHub suffixes repeats: `#notes`, `#notes-1`, `#notes-2`."""
        seen: dict = {}
        self.assertEqual(_github_slug("Notes", seen), "notes")
        self.assertEqual(_github_slug("Notes", seen), "notes-1")
        self.assertEqual(_github_slug("Notes.", seen), "notes-2")
        # Without a `seen` dict there is no dedupe state at all.
        self.assertEqual(_github_slug("Notes"), "notes")

    def test_open_issues_anchor_set_uses_github_rule_and_dedupes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "open_issues.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("## LOW\n\n"
                        "### L16. Seeding vs `unlocking_technologies` warnings (1.13.9+)\n\n"
                        "### Notes\n\n"
                        "### Notes\n")
            anchors = _open_issues_anchors(path)
            self.assertIn("l16-seeding-vs-unlocking_technologies-warnings-1139", anchors)
            self.assertIn("notes", anchors)
            self.assertIn("notes-1", anchors)
            # The pre-fix rule collapsed the underscore run to a dash — must be gone.
            self.assertNotIn("l16-seeding-vs-unlocking-technologies-warnings-1-13-9", anchors)


class RegistryCacheInvalidationTests(unittest.TestCase):
    """The registry cache reads open_issues.md inside the memoized computation, so
    its mtime has to take part in the cache key — otherwise fixing a heading never
    clears the stale `does not resolve` warning."""

    def test_cache_invalidates_when_open_issues_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            audits = os.path.join(tmp, "audits")
            vanilla = os.path.join(tmp, "vanilla")
            os.makedirs(audits, exist_ok=True)
            os.makedirs(vanilla, exist_ok=True)
            open_issues = os.path.join(audits, "open_issues.md")
            doc = os.path.join(vanilla, "vanilla_known_bugs.md")
            with open(doc, "w", encoding="utf-8") as f:
                f.write("""
## Mod-side cosmetic, tracked-not-fixed (source-anchored)

### `some.cpp:1` — placeholder
- source: `some.cpp:1`
- tracked: `docs/audits/open_issues.md#l20-renamed-heading`

```
signature
```
""")
            _vanilla_bug_cache.clear()

            # Heading doesn't exist yet -> warning, and the result is memoized.
            with open(open_issues, "w", encoding="utf-8") as f:
                f.write("## LOW\n\n### L20. old heading\n")
            _, _, _, warnings = load_vanilla_bug_registry(doc)
            self.assertTrue(any("does not resolve" in w for w in warnings))

            # Fix ONLY open_issues.md (registry file untouched, cache not cleared).
            doc_mtime_before = os.path.getmtime(doc)
            with open(open_issues, "w", encoding="utf-8") as f:
                f.write("## LOW\n\n### L20. renamed heading\n")
            # Force a distinct mtime so the test can't pass/fail on filesystem
            # timestamp granularity.
            os.utime(open_issues, (time.time() + 10, time.time() + 10))

            _, _, _, warnings2 = load_vanilla_bug_registry(doc)
            self.assertEqual(warnings2, [], "stale cached warning survived an open_issues.md edit")
            self.assertEqual(os.path.getmtime(doc), doc_mtime_before)


class GuiInjectedScopeTests(unittest.TestCase):
    """tag_gui_injected_scopes: open_issues.md L14, the validator's never-set lines
    for scopes a .gui or loc string sets with AddScope."""

    NEVER_SET = "Event target '{}' is used but is never set. Setting it in an unused scripted trigger or effect does not count"

    def _entry(self, message):
        return LogEntry("00:00:00", "jomini_effect.cpp:1139", message)

    def test_tags_only_names_a_mod_file_sets(self):
        with tempfile.TemporaryDirectory() as d:
            gui = os.path.join(d, "gui")
            loc = os.path.join(d, "localization", "english")
            os.makedirs(gui)
            os.makedirs(loc)
            with open(os.path.join(gui, "panel.gui"), "w", encoding="utf-8-sig") as f:
                f.write("datacontext = \"[TopScope.AddScope('row_army', MakeScopeValue(TopScope.ScriptValue('x')))]\"\n")
            with open(os.path.join(loc, "x_l_english.yml"), "w", encoding="utf-8-sig") as f:
                f.write("l_english:\n k:0 \"[GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'sr_rival', GetPlayer.MakeScope ).End]\"\n")
            names = gui_injected_scope_names([gui, loc])
            self.assertEqual(names, frozenset({"row_army", "sr_rival"}))

            gui_row = self._entry(self.NEVER_SET.format("row_army"))
            loc_row = self._entry(self.NEVER_SET.format("sr_rival"))
            unset = self._entry(self.NEVER_SET.format("row_navy"))
            variable = self._entry("Variable 'row_army' is used but is never set")
            tag_gui_injected_scopes([gui_row, loc_row, unset, variable], names)

            for e in (gui_row, loc_row):
                self.assertIsNotNone(e.vanilla_bug_ref)
                self.assertEqual(e.vanilla_bug_ref["kind"], "mod_low_priority")
                self.assertEqual(e.vanilla_bug_ref["tracked_issue"], GUI_INJECTED_SCOPE_REF.tracked_issue)
            # A name nothing sets is a real bug, and a variable is not a scope.
            self.assertIsNone(unset.vanilla_bug_ref)
            self.assertIsNone(variable.vanilla_bug_ref)

    def test_keeps_an_earlier_registry_tag(self):
        e = self._entry(self.NEVER_SET.format("base_market"))
        e.vanilla_bug_ref = {"title": "registry", "section": "x", "kind": "mod_low_priority"}
        tag_gui_injected_scopes([e], frozenset({"base_market"}))
        self.assertEqual(e.vanilla_bug_ref["title"], "registry")

    def test_sees_a_name_added_after_the_first_call(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "panel.gui")
            with open(path, "w", encoding="utf-8") as f:
                f.write("AddScope('a', x)\n")
            self.assertEqual(gui_injected_scope_names([d]), frozenset({"a"}))
            with open(path, "w", encoding="utf-8") as f:
                f.write("AddScope('a', x) AddScope('b', y)\n")
            os.utime(path, (time.time() + 10, time.time() + 10))
            self.assertEqual(gui_injected_scope_names([d]), frozenset({"a", "b"}))

    def test_ref_anchors_resolve_to_real_headings(self):
        root = os.path.dirname(os.path.abspath(__file__))
        doc, _, slug = GUI_INJECTED_SCOPE_REF.anchor.partition("#")
        with open(os.path.join(root, doc), encoding="utf-8") as f:
            seen: dict[str, int] = {}
            slugs = {_github_slug(line[4:].strip(), seen) for line in f if line.startswith("### ")}
        self.assertIn(slug, slugs)
        issue_doc, _, issue_slug = GUI_INJECTED_SCOPE_REF.tracked_issue.partition("#")
        self.assertIn(issue_slug, _open_issues_anchors(os.path.join(root, issue_doc)))


class ModGuiFetchUntagTests(unittest.TestCase):
    """untag_mod_gui_fetches (#1269): three vanilla_known_bugs.md entries match
    a cpp source and a generic message, so a mod GUI's data-context failure,
    whose lines name no file, was hidden as vanilla noise. A line whose key or
    data type the mod's own GUI reaches loses the generic tag; one only
    vanilla's GUI reaches keeps it."""

    WANTED = "No context supplied (Use SetDataContext), wanted context of type '{}' for '{} '"
    FETCH = "FetchData failed for '{}'"
    LOCALIZED = "PdxDataFetchLocalizedData failed for '{}'"

    OWN = "gui/te_census_widgets.gui"
    COPY = "gui/00_te_country_panel_information.gui"
    LOC = "localization/english/te_census_l_english.yml"
    # te_census_widgets.gui has no vanilla counterpart: the mod's own.
    OWN_GUI = (
        "types te_census {\n"
        "\ttype te_census_income = flowcontainer {\n"
        "\t\ttextbox = {\n"
        "\t\t\ttext = \"POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL\"\n"
        "\t\t\ttooltip = \"POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL_TOOLTIP\"\n"
        "\t\t}\n"
        "\t\t# text = \"COMMENTED_OUT_LABEL\"\n"
        "\t\ttextbox = { raw_text = \"#v [Character.GetFullName]#!\" }\n"
        "\t\ttextbox = { text = \"[SelectLocalization( Country.IsAI, 'te_census_ai', 'te_census_own' )]\" }\n"
        "\t\ttextbox = { visible = \"[GetVariableSystem.Exists('te_census_open')]\" }\n"
        "\t\ttextbox = { text = \"te_census_scopes\" tooltip = \"[GetPlayer.GetName]\" }\n"
        "\t\ttextbox = { text = \"te_census_player\" visible = \"[GetPlayer.MakeScope.Var( 'te_census_on' ).IsSet]\" }\n"
        "\t}\n"
        "}\n"
    )
    # pops_overview.gui replaces vanilla's panel and carries vanilla's own keys.
    OVERRIDE_GUI = (
        "window = {\n"
        "\tdatacontext = \"[PopsOverviewPanel.GetMapModeList]\"\n"
        "\ttextbox = { text = \"POPS_OVERVIEW_TITLE\" tooltip = \"[CulturalCommunity.GetName]\" }\n"
        "\ttextbox = { text = \"te_panel_income\" }\n"
        "}\n"
    )
    # A generated copy of a vanilla type under a mod file name (gotcha #30):
    # vanilla's markup, less the block the generator marks.
    COPY_GUI = (
        "### AUTO-GENERATED. Copied from vanilla; only the `### MOD: Nation tab` block differs.\n"
        "types te_country_panel_information {\n"
        "\ttype country_panel_information_content = flowcontainer {\n"
        "\t\ttextbox = { text = \"COUNTRY_GOVERNMENT\" tooltip = \"[Amendment.GetName]\" }\n"
        "\t\ttextbox = { text = \"te_copy_outside\" }\n"
        "\t\t### MOD: Nation tab: the list moved\n"
        "\t\ttextbox = { text = \"te_nation_panel_line\" visible = \"[TimedModifier.IsValid]\" }\n"
        "\t\t### END MOD ###\n"
        "\t\ttextbox = { text = \"COUNTRY_RANK\" }\n"
        "\t}\n"
        "}\n"
    )
    MOD_LOC = (
        "l_english:\n"
        " te_census_ai:0 \"$te_census_nested$ of the AI\"\n"
        " te_census_own:0 \"Yours\"\n"
        " te_census_nested:0 \"[JournalEntry.GetName]\"\n"
        " te_census_scopes:0 \"[SCOPE.sCountry('x').GetName] [ROOT.GetCountry.GetName] [TARGET_COUNTRY.GetName]"
        " [THIS.GetName]\"\n"
        " te_event_desc:0 \"The [InterestGroup.GetName] object of [GetPlayer.GetGovernment.GetName].\"\n"
        " te_census_player:0 \"In [GetPlayer.GetCapital.GetStateRegion.GetName|v]\"\n"
        " te_panel_income:0 \"Income\"\n"
        " te_copy_outside:0 \"Outside\"\n"
        " te_nation_panel_line:0 \"Modifiers\"\n"
        " POPS_OVERVIEW_TITLE:0 \"People\"\n"
    )
    VANILLA_LOC = {
        "POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL": "@money![PopsOverviewPanel.GetAverageIncomeRich|v1] Income",
        "POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL_TOOLTIP":
            "#header Average Income#!\\n@money![PopsOverviewPanel.GetAverageIncomeRich|v1]",
        "POPS_OVERVIEW_TITLE": "Population",
        "COUNTRY_GOVERNMENT": "[Country.GetGovernment.GetName]",
        "COUNTRY_RANK": "Rank",
        "INCORPORATION_TIME_SAME_TRAIT_GROUP": "shares the [DiscriminationTraitGroup.GetName] with",
    }
    GENERIC = (
        "\n### `pdx_data_callstack.cpp:16` — vanilla data context not supplied\n"
        "- source: `pdx_data_callstack.cpp:16`\n\n"
        "```\nNo context supplied (Use SetDataContext), wanted context of type\n```\n"
    )
    NAMING = (
        "\n### `pdx_data_callstack.cpp:16` — {title}\n"
        "- source: `pdx_data_callstack.cpp:16`\n{field}\n"
        "```\nwanted context of type 'Country' for 'Country.GetFoo\n```\n"
    )

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.mod = os.path.join(self._tmp.name, "mod")
        self.install = os.path.join(self._tmp.name, "install")
        self._write(self.mod, self.OWN, self.OWN_GUI)
        self._write(self.mod, "gui/pops_overview.gui", self.OVERRIDE_GUI)
        self._write(self.mod, self.COPY, self.COPY_GUI)
        self._write(self.mod, self.LOC, self.MOD_LOC)
        self._write(self.install, "game/gui/pops_overview.gui", "")
        self._write(self.install, "jomini/gui/Shared/Windows.gui", "")
        self._write(self.install, "clausewitz/gui/console.gui", "")
        root = os.path.dirname(os.path.abspath(__file__))
        _vanilla_bug_cache.clear()
        # This checkout's registries: their three source-only entries are the ones at issue.
        _, self.vanilla_basename, self.vanilla_source, _ = load_vanilla_bug_registry(
            os.path.join(root, "docs", "vanilla", "vanilla_known_bugs.md"))
        _, _, self.noise_source, _ = load_mod_noise_registry(
            os.path.join(root, "docs", "audits", "mod_known_noise.md"))

    @staticmethod
    def _write(root, rel, text, encoding="utf-8-sig"):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding=encoding) as f:
            f.write(text)
        return path

    def _refs(self):
        return mod_gui_references(self.mod, vanilla_gui_file_names(self.install), self.VANILLA_LOC)

    def _tagged(self, rows):
        entries = [LogEntry("02:19:22", source, message) for source, message in rows]
        tag_vanilla_bugs(entries, self.vanilla_basename, self.vanilla_source, mod_root=self.mod)
        return entries

    def _untag(self, entries, refs=None):
        untag_mod_gui_fetches(entries, refs or self._refs(), (self.vanilla_source, self.noise_source),
                              mod_root=self.mod)

    def _flood(self, key, type_, chain):
        return self._tagged([
            ("pdx_data_callstack.cpp:16", self.WANTED.format(type_, chain)),
            ("pdx_data_localize_helper.cpp:286", self.FETCH.format(chain)),
            ("pdx_gui_localize.cpp:140", self.LOCALIZED.format(key)),
        ])

    def test_the_2026_10_31_flood_comes_back_untagged_and_vanillas_own_stays_tagged(self):
        ours = self._flood("POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL", "PopsOverviewPanel",
                           "PopsOverviewPanel.GetAverageIncomeRich")
        vanillas = self._flood("INCORPORATION_TIME_SAME_TRAIT_GROUP", "DiscriminationTraitGroup",
                               "DiscriminationTraitGroup.GetName")
        # The gap: the registry files all six under vanilla's engine noise.
        for e in ours + vanillas:
            self.assertEqual((e.vanilla_bug_ref or {}).get("kind"), "vanilla_noise", e.message)
        titles = [e.vanilla_bug_ref["title"] for e in ours]

        self._untag(ours + vanillas)

        for e, title in zip(ours, titles):
            self.assertIsNone(e.vanilla_bug_ref, e.message)
            self.assertEqual(e.mod_gui_context["files"], [self.OWN])
            self.assertEqual(e.mod_gui_context["file_count"], 1)
            self.assertEqual(e.mod_gui_context["untagged_from"], title)
            self.assertEqual(e.to_dict()["mod_gui_context"], e.mod_gui_context)
        self.assertEqual([e.mod_gui_context.get("type") for e in ours],
                         ["PopsOverviewPanel", "PopsOverviewPanel", None])
        self.assertEqual(ours[2].mod_gui_context["key"], "POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL")
        for e in vanillas:
            self.assertEqual(e.vanilla_bug_ref["kind"], "vanilla_noise", e.message)
            self.assertIsNone(e.mod_gui_context)
            self.assertNotIn("mod_gui_context", e.to_dict())
        # What the canonical view keeps is the mod's three lines.
        shown = apply_known_noise_modes(ours + vanillas, "hide", "hide")
        self.assertEqual(shown, ours)

    def test_what_the_mods_own_markup_reaches(self):
        refs = self._refs()
        own = (self.OWN,)
        # text/tooltip/raw_text values, a quoted key in an expression, and the
        # key that one nests; a commented-out line and a variable name are not keys.
        for key in ("POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL", "POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL_TOOLTIP",
                    "#v [Character.GetFullName]#!", "te_census_ai", "te_census_own", "te_census_nested"):
            self.assertEqual(refs.keys.get(key), own, key)
        self.assertNotIn("COMMENTED_OUT_LABEL", refs.keys)
        self.assertNotIn("te_census_open", refs.keys)
        # Heads of the chains in the file and in the values its keys reach.
        for name in ("Character", "Country", "PopsOverviewPanel", "JournalEntry"):
            self.assertEqual(refs.types.get(name), own, name)
        for name in ("SelectLocalization", "IsAI", "GetName", "Exists", "DiscriminationTraitGroup"):
            self.assertNotIn(name, refs.types)
        # A global function is no data type; its expressions are kept whole.
        for name in ("GetPlayer", "GetVariableSystem"):
            self.assertNotIn(name, refs.types)
        self.assertEqual(set(refs.expressions), {
            "GetVariableSystem.Exists('te_census_open')", "GetPlayer.GetName",
            "GetPlayer.MakeScope.Var('te_census_on').IsSet", "GetPlayer.GetCapital.GetStateRegion.GetName|v"})
        self.assertTrue(all(files == own for files in refs.expressions.values()))

    def test_a_global_function_head_needs_the_mods_own_markup_to_write_the_expression(self):
        """Every panel calls GetPlayer, and it heads one in twenty of vanilla's
        own expressions, so reading it says nothing. Such a line is the mod's
        only when the expression itself is one the mod's own markup writes."""
        rows = [
            # Vanilla's own: the mod writes no such expression.
            (self.FETCH.format("GetPlayer.GetCapital.GetName"), None),
            (self.LOCALIZED.format("#b [GetPlayer.GetCapital.GetName]#!"), None),
            # Written in the mod's own .gui, as the engine prints it (its own spacing).
            (self.FETCH.format("GetPlayer.MakeScope.Var('te_census_on').IsSet"), self.OWN),
            (self.FETCH.format("GetPlayer.MakeScope.Var( 'te_census_on' ).IsSet "), self.OWN),
            # Written in a loc value the mod's own .gui draws (the format suffix is not part of it).
            (self.FETCH.format("GetPlayer.GetCapital.GetStateRegion.GetName"), self.OWN),
            # The start of what the mod writes, or a longer name, is another expression.
            (self.FETCH.format("GetPlayer.GetCapital.GetStateRegion"), None),
            (self.FETCH.format("GetPlayer.GetCapital.GetStateRegion.GetNameNoFormatting"), None),
            (self.FETCH.format("GetPlayer.MakeScope.Var('te_census_on')"), None),
            # In a mod loc value no mod-owned .gui draws: not the GUI's reach.
            (self.FETCH.format("GetPlayer.GetGovernment.GetName"), None),
        ]
        entries = self._tagged([("pdx_gui_localize.cpp:140" if "Localized" in message
                                 else "pdx_data_localize_helper.cpp:286", message) for message, _ in rows])
        self.assertTrue(all(e.vanilla_bug_ref for e in entries))
        self._untag(entries)
        for e, (_, file) in zip(entries, rows):
            with self.subTest(message=e.message):
                if file is None:
                    self.assertIsNotNone(e.vanilla_bug_ref)
                else:
                    self.assertIsNone(e.vanilla_bug_ref)
                    self.assertEqual(e.mod_gui_context["files"], [file])
                    self.assertIn("GetPlayer.", e.mod_gui_context["expression"])

    def test_script_loc_scope_names_and_types_only_other_mod_loc_reads_are_no_data_types(self):
        refs = self._refs()
        # te_census_scopes is drawn by the mod's own file, and its value reads
        # only scopes: names with no lower-case letter.
        self.assertEqual(refs.keys["te_census_scopes"], (self.OWN,))
        for name in ("SCOPE", "ROOT", "THIS", "TARGET_COUNTRY"):
            self.assertNotIn(name, refs.types)
        # No mod-owned GUI draws te_event_desc, so what it reads is not reached.
        self.assertNotIn("InterestGroup", refs.types)
        rows = self._tagged([
            ("pdx_data_callstack.cpp:16", self.WANTED.format("SCOPE", "SCOPE.GetRootScope.GetCountry")),
            ("pdx_data_localize_helper.cpp:286",
             self.FETCH.format("SCOPE.GetRootScope.GetCountry.GetPowerBloc.GetParticipantWithHighestLibertyDesire.GetName")),
            ("pdx_data_callstack.cpp:16", self.WANTED.format("InterestGroup", "InterestGroup.GetName")),
        ])
        self._untag(rows, refs)
        self.assertTrue(all(e.vanilla_bug_ref for e in rows))

    def test_an_override_of_a_vanilla_file_carries_vanillas_keys_and_types(self):
        refs = self._refs()
        self.assertNotIn("POPS_OVERVIEW_TITLE", refs.keys)
        self.assertNotIn("CulturalCommunity", refs.types)
        # PopsOverviewPanel is there through the key the mod's own file draws,
        # not through the override's datacontext.
        self.assertEqual(refs.types["PopsOverviewPanel"], (self.OWN,))
        e = self._tagged([("pdx_data_callstack.cpp:16",
                           self.WANTED.format("CulturalCommunity", "CulturalCommunity.GetName"))])[0]
        self._untag([e], refs)
        self.assertIsNotNone(e.vanilla_bug_ref)

    def test_only_the_marked_blocks_of_a_copy_of_vanilla_types_are_the_mods(self):
        """gotcha #30: 00_te_country_panel_information.gui redefines a vanilla
        type from a mod file name. Outside `### MOD:` / `### END MOD ###` it is
        vanilla's markup, vanilla's keys and all."""
        refs = self._refs()
        for key in ("COUNTRY_GOVERNMENT", "COUNTRY_RANK"):
            self.assertNotIn(key, refs.keys)
        self.assertNotIn("Amendment", refs.types)
        self.assertEqual(refs.keys["te_nation_panel_line"], (self.COPY,))
        self.assertEqual(refs.types["TimedModifier"], (self.COPY,))
        rows = self._tagged([
            ("pdx_gui_localize.cpp:140", self.LOCALIZED.format("COUNTRY_GOVERNMENT")),
            ("pdx_data_callstack.cpp:16", self.WANTED.format("Amendment", "Amendment.GetName")),
            ("pdx_data_callstack.cpp:16", self.WANTED.format("TimedModifier", "TimedModifier.IsValid")),
        ])
        self._untag(rows, refs)
        self.assertEqual([e.vanilla_bug_ref is None for e in rows], [False, False, True])
        # A mark that is never closed is a comment, and the file counts whole.
        self._write(self.mod, "gui/te_notes.gui",
                    "### MOD: a note, not a block\ntextbox = { text = \"[Hull.GetName]\" }\n")
        self.assertEqual(self._refs().types.get("Hull"), ("gui/te_notes.gui",))

    def test_a_key_only_the_mods_loc_defines_is_the_mods_whichever_file_draws_it(self):
        refs = self._refs()
        self.assertEqual(refs.mod_loc_keys["te_event_desc"], self.LOC)
        self.assertNotIn("POPS_OVERVIEW_TITLE", refs.mod_loc_keys)  # the mod restates vanilla's key
        # Named outside the mod's own markup: the override, and the copy's vanilla part.
        self.assertEqual(refs.keys["te_panel_income"], ("gui/pops_overview.gui",))
        self.assertEqual(refs.keys["te_copy_outside"], (self.COPY,))
        rows = self._tagged([("pdx_gui_localize.cpp:140", self.LOCALIZED.format(key))
                             for key in ("te_panel_income", "te_event_desc", "POPS_OVERVIEW_TITLE")])
        self._untag(rows, refs)
        self.assertEqual([e.vanilla_bug_ref is None for e in rows], [True, True, False])
        self.assertEqual(rows[0].mod_gui_context["files"], ["gui/pops_overview.gui"])
        self.assertEqual(rows[1].mod_gui_context["files"], [self.LOC])  # no .gui names it
        # What the override's key reads is not the mod's own GUI's reach.
        self.assertEqual(refs.types.get("PopsOverviewPanel"), (self.OWN,))

    def test_the_payload_shapes(self):
        refs = self._refs()
        rows = [
            ("pdx_data_callstack.cpp:16", self.WANTED.format("JournalEntry", "JournalEntry.GetCountry.MakeScope"), "type"),
            # The wanted type alone: GetPlayer, an argument here, is not the subject.
            ("pdx_data_callstack.cpp:16",
             self.WANTED.format("BuildingType", "BuildingType.GetNameForCountry( GetPlayer.Self )"), None),
            # An expression with quoted arguments: the last quote closes the
            # payload, and its head decides.
            ("pdx_data_localize_helper.cpp:286",
             self.FETCH.format("JournalEntry.GetCountry.MakeScope.Var( 'x' ).GetValue"), "type"),
            ("pdx_data_localize_helper.cpp:286", self.FETCH.format("Building.GetExpansionCost( GetPlayer.Self )"), None),
            # Inline text a mod-owned file draws, and bracketed payloads it does not.
            ("pdx_gui_localize.cpp:302", self.LOCALIZED.format("#v [Character.GetFullName]#!"), "key"),
            ("pdx_gui_localize.cpp:140", self.LOCALIZED.format("#b [Country.GetName]#!"), "type"),
            ("pdx_gui_localize.cpp:140", self.LOCALIZED.format("#b [Building.GetName] of [Country.GetName]#!"), "type"),
            ("pdx_gui_localize.cpp:140", self.LOCALIZED.format("#b [InterestGroup.GetName]#!"), None),
            # A vanilla key nothing of the mod's draws, with no chain of its own.
            ("pdx_gui_localize.cpp:140", self.LOCALIZED.format("COUNTRY_RANK"), None),
            ("pdx_data_localize_helper.cpp:286", self.FETCH.format("Building.GetName"), None),
        ]
        entries = self._tagged([(source, message) for source, message, _ in rows])
        self.assertTrue(all(e.vanilla_bug_ref for e in entries))
        self._untag(entries, refs)
        for e, (_, _, expected) in zip(entries, rows):
            with self.subTest(message=e.message):
                if expected is None:
                    self.assertIsNotNone(e.vanilla_bug_ref)
                    self.assertIsNone(e.mod_gui_context)
                else:
                    self.assertIsNone(e.vanilla_bug_ref)
                    self.assertIn(expected, e.mod_gui_context)

    def _registered(self, vanilla_doc, noise_doc="## Entries\n"):
        """A `wanted context of type 'Country'` line through both registries
        and the pass, with a mod-owned GUI that reads Country."""
        docs = os.path.join(self._tmp.name, "repo")
        self._write(docs, "docs/audits/open_issues.md", "## LOW\n\n### L1 thing\n", "utf-8")
        vanilla = self._write(docs, "docs/vanilla/vanilla_known_bugs.md",
                              "## Engine noise (source-anchored)\n" + vanilla_doc, "utf-8")
        noise = self._write(docs, "docs/audits/mod_known_noise.md", noise_doc, "utf-8")
        _vanilla_bug_cache.clear()
        _, vb, vs, w1 = load_vanilla_bug_registry(vanilla)
        _, mb, ms, w2 = load_mod_noise_registry(noise)
        self.assertEqual(w1 + w2, [])
        e = LogEntry("01:00:00", "pdx_data_callstack.cpp:16", self.WANTED.format("Country", "Country.GetFoo"))
        tag_vanilla_bugs([e], vb, vs, mod_root=self.mod)
        tag_vanilla_bugs([e], mb, ms, mod_root=self.mod)
        untag_mod_gui_fetches([e], self._refs(), (vs, ms), mod_root=self.mod)
        return e, bool(apply_known_noise_modes([e], "hide", "hide"))

    def test_a_line_the_pass_shows_can_be_registered_or_watched(self):
        """Whatever the pass lets through must be disposable by the registry:
        an entry whose signature names the line keeps or gets its tag, of any
        kind, in either document order. Only the generic entry is overridden."""
        vanilla_named = self.NAMING.format(title="vanilla's lens reads Country.GetFoo", field="")
        watch = "\n## Watch list (tagged, never hidden)\n" + self.NAMING.format(
            title="Country.GetFoo, vanilla's or ours", field="- check: read the lens\n")
        noise = "## Entries\n" + self.NAMING.format(
            title="our Country.GetFoo read", field="- tracked: `docs/audits/open_issues.md#l1-thing`\n")
        layouts = [
            # (label, vanilla registry, mod-noise registry, kind after, title after, shown in the clean view)
            ("the generic entry alone", self.GENERIC, None, None, None, True),
            ("a naming vanilla entry before the generic one", vanilla_named + self.GENERIC, None,
             "vanilla_noise", "vanilla's lens reads Country.GetFoo", False),
            ("a naming vanilla entry after the generic one", self.GENERIC + vanilla_named, None,
             "vanilla_noise", "vanilla's lens reads Country.GetFoo", False),
            ("a naming vanilla entry alone", vanilla_named, None,
             "vanilla_noise", "vanilla's lens reads Country.GetFoo", False),
            ("a watch-list entry after the generic one", self.GENERIC + watch, None,
             WATCH_KIND, "Country.GetFoo, vanilla's or ours", True),
            ("a mod-noise entry beside the generic one", self.GENERIC, noise,
             "mod_low_priority", "our Country.GetFoo read", False),
        ]
        for label, vanilla_doc, noise_doc, kind, title, shown in layouts:
            with self.subTest(layout=label):
                e, in_clean_view = self._registered(vanilla_doc, noise_doc or "## Entries\n")
                ref = e.vanilla_bug_ref or {}
                self.assertEqual((ref.get("kind"), ref.get("title")), (kind, title))
                self.assertEqual(in_clean_view, shown)
                # Only the line nothing names carries the mod's files.
                self.assertEqual(e.mod_gui_context is not None, kind is None)

    def test_only_a_vanilla_tag_on_one_of_the_three_lines_is_cleared(self):
        refs = self._refs()
        message = self.WANTED.format("PopsOverviewPanel", "PopsOverviewPanel.GetAverageIncomeRich")
        for kind in ("mod_low_priority", WATCH_KIND):
            e = LogEntry("00:00:00", "pdx_data_callstack.cpp:16", message)
            e.vanilla_bug_ref = {"title": "registered on purpose", "section": "x", "kind": kind}
            self._untag([e], refs)
            self.assertEqual(e.vanilla_bug_ref["kind"], kind)
            self.assertIsNone(e.mod_gui_context)
        # A vanilla tag no generic source entry made (a path anchor, say) stays.
        pathed = LogEntry("00:00:00", "pdx_data_callstack.cpp:16", message)
        pathed.vanilla_bug_ref = {"title": "a path-anchored entry", "section": "x", "kind": "vanilla"}
        self._untag([pathed], refs)
        self.assertIsNotNone(pathed.vanilla_bug_ref)
        # The same words from another cpp file are another entry's business.
        other = LogEntry("00:00:00", "pdx_assert.cpp:637", message)
        other.vanilla_bug_ref = {"title": "an assert", "section": "x", "kind": "vanilla_noise"}
        self._untag([other], refs)
        self.assertIsNotNone(other.vanilla_bug_ref)
        # An entry no registry tagged is left as it is.
        bare = LogEntry("00:00:00", "pdx_data_callstack.cpp:16", message)
        self._untag([bare], refs)
        self.assertIsNone(bare.vanilla_bug_ref)
        self.assertIsNone(bare.mod_gui_context)

    def test_a_cached_entry_is_judged_afresh_on_every_run(self):
        """parse_log hands the same LogEntry objects to every request."""
        e = self._flood("POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL", "PopsOverviewPanel",
                        "PopsOverviewPanel.GetAverageIncomeRich")[2]
        self._untag([e])
        self.assertIsNotNone(e.mod_gui_context)
        # The widget stops drawing the key; the next request re-tags and re-reads.
        path = self._write(self.mod, self.OWN, "types te_census { }\n")
        os.utime(path, (time.time() + 10, time.time() + 10))
        self.assertNotIn("POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL", self._refs().keys)
        tag_vanilla_bugs([e], self.vanilla_basename, self.vanilla_source, mod_root=self.mod)
        self._untag([e])
        self.assertIsNotNone(e.vanilla_bug_ref)
        self.assertIsNone(e.mod_gui_context)

    def test_without_the_vanilla_gui_folder_only_the_mods_own_keys_are_untagged(self):
        self.assertIsNone(vanilla_gui_file_names(None))
        self.assertIsNone(vanilla_gui_file_names(os.path.join(self._tmp.name, "no_install")))
        refs = mod_gui_references(self.mod, None, self.VANILLA_LOC)
        self.assertEqual(refs.warnings, (MOD_GUI_UNTAG_NO_INSTALL,))
        self.assertEqual(refs.types, {})
        # No file can be called the mod's own, so only mod-only keys are listed,
        # under whichever file names them.
        self.assertEqual(set(refs.keys), {"te_census_scopes", "te_panel_income", "te_copy_outside",
                                          "te_nation_panel_line", "te_census_ai", "te_census_own",
                                          "te_census_player"})
        self.assertEqual(refs.expressions, {})
        ours = self._flood("POPS_OVERVIEW_AVERAGE_INCOME_UPPER_LABEL", "PopsOverviewPanel",
                           "PopsOverviewPanel.GetAverageIncomeRich")
        own_key = self._tagged([("pdx_gui_localize.cpp:140", self.LOCALIZED.format("te_event_desc"))])
        self._untag(ours + own_key, refs)
        self.assertTrue(all(e.vanilla_bug_ref for e in ours))
        self.assertIsNone(own_key[0].vanilla_bug_ref)
        self.assertEqual(self._refs().warnings, ())

    def test_what_cannot_be_built_is_warned_about_and_still_cached(self):
        names = vanilla_gui_file_names(self.install)
        # No loc snapshot: the same refs object on the next call, not a rebuild.
        with mock.patch("game_log_reader._VANILLA_LOC_SNAPSHOT", os.path.join(self._tmp.name, "none.json")):
            refs = mod_gui_references(self.mod, names)
            self.assertIs(mod_gui_references(self.mod, names), refs)
        self.assertEqual(refs.warnings, (MOD_GUI_UNTAG_NO_VANILLA_LOC,))
        self.assertEqual(refs.mod_loc_keys, {})  # nothing to tell a mod-only key by
        self.assertIn("PopsOverviewPanel", self._refs().types)
        self.assertNotIn("PopsOverviewPanel", refs.types)  # the vanilla key was not followed
        # A folder that is not the mod's checkout.
        nowhere = mod_gui_references(os.path.join(self._tmp.name, "not_the_mod"), names, self.VANILLA_LOC)
        self.assertEqual(len(nowhere.warnings), 1)
        self.assertIn("no .gui file under", nowhere.warnings[0])
        # A caller that logs the warnings says each once per process.
        game_log_reader._mod_gui_warned.clear()
        self.assertEqual(new_mod_gui_warnings(refs), [MOD_GUI_UNTAG_NO_VANILLA_LOC])
        self.assertEqual(new_mod_gui_warnings(refs), [])

    def test_vanilla_gui_file_names_are_the_mounted_paths_of_all_three_trees(self):
        self.assertEqual(vanilla_gui_file_names(self.install), frozenset({
            "gui/pops_overview.gui", "gui/shared/windows.gui", "gui/console.gui"}))
        # Matched without case, as the game's file system does.
        self._write(self.mod, "gui/Shared/windows.gui", "textbox = { text = \"SHARED_WINDOW_TITLE\" }\n")
        self.assertNotIn("SHARED_WINDOW_TITLE", self._refs().keys)

    def test_a_vanilla_key_is_followed_through_the_committed_loc_snapshot_by_default(self):
        """The server and log_triage.py pass no vanilla loc: the key the Census
        window drew on 2026-10-31 must still lead to PopsOverviewPanel."""
        refs = mod_gui_references(self.mod, vanilla_gui_file_names(self.install))
        self.assertEqual(refs.warnings, ())
        self.assertEqual(refs.types.get("PopsOverviewPanel"), (self.OWN,))


class HelperAnchorTests(unittest.TestCase):
    """#730: an entry anchored on a vanilla helper file the mod calls into
    also tags the mod's errors through that helper (error.log lists the whole
    call stack), so the registry check warns until the entry is re-anchored or
    carries `- reviewed: helper anchor, ...`."""

    REGISTRY = """
## Script errors observed

### `common/scripted_effects/00_lobby_effects.txt:12` — appeasement change on a lobby

```
change_appeasement effect [ Wrong scope
```

### `common/scripted_triggers/00_diplomacy_triggers.txt` — narrow enough
- reviewed: helper anchor, signature cannot match a mod call (only `unused_trigger` logs it; see `common/scripted_triggers/not_an_anchor.txt`)

```
Something vanilla-only
```

### `events/some_vanilla_events.txt:5` — anchored on a caller, not a helper

```
Error
```
"""

    def _setup(self, tmp: str, mod_files: dict[str, str]) -> tuple[list, str]:
        docs = os.path.join(tmp, "docs")
        os.makedirs(os.path.join(docs, "vanilla"))
        os.makedirs(os.path.join(docs, "audits"))
        with open(os.path.join(docs, "audits", "open_issues.md"), "w", encoding="utf-8") as f:
            f.write("")
        doc = os.path.join(docs, "vanilla", "vanilla_known_bugs.md")
        with open(doc, "w", encoding="utf-8") as f:
            f.write(self.REGISTRY)
        _vanilla_bug_cache.clear()
        game = os.path.join(tmp, "vanilla", "game")
        files = {
            "common/scripted_effects/00_lobby_effects.txt":
                "add_lobby_appeasement = { change_appeasement = $AMOUNT$ }\nunused_effect = { }\n",
            "common/scripted_triggers/00_diplomacy_triggers.txt": "has_treaty_alliance_with = { }\n",
            "events/some_vanilla_events.txt": "",
        }
        for rel, text in files.items():
            path = os.path.join(game, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        mod = os.path.join(tmp, "mod")
        for rel, text in mod_files.items():
            path = os.path.join(mod, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        refs, _, _, warnings = load_vanilla_bug_registry(doc)
        self.assertEqual(warnings, [])
        return refs, mod, game

    def test_reviewed_line_is_parsed_and_never_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, _, _ = self._setup(tmp, {})
        narrow = refs[1]
        self.assertEqual(narrow.file_basenames, ["00_diplomacy_triggers.txt"])
        self.assertTrue(narrow.reviewed[0].startswith("helper anchor, signature cannot match"))

    def test_mod_call_through_the_helper_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, mod, game = self._setup(tmp, {
                "events/social_tensions_events.txt": (
                    "namespace = st\n"
                    "st.1 = {\n"
                    "\toption = {\n"
                    "\t\tadd_lobby_appeasement = { AMOUNT = 1 }\n"
                    "\t\thas_treaty_alliance_with = yes\n"
                    "\t}\n"
                    "}\n"
                ),
            })
            out = helper_anchor_warnings(refs, mod, game)
        self.assertEqual(len(out), 1)
        w = out[0]
        self.assertEqual(w["kind"], "helper_anchor_mod_calls")
        self.assertEqual(w["label"], "vanilla_bug_registry")
        self.assertEqual(w["anchor"], "00_lobby_effects.txt")
        self.assertEqual(w["helper_file"], "common/scripted_effects/00_lobby_effects.txt")
        self.assertEqual(w["mod_uses"], {"add_lobby_appeasement": ["events/social_tensions_events.txt:4"]})
        self.assertIn("anchor on the vanilla caller", w["advice"])
        self.assertIn("appeasement change on a lobby", w["detail"])

    def test_vanilla_only_stack_entry_is_skipped(self):
        # #863: an error through the mod's call has the mod file in its stack,
        # which a `- stack: vanilla only` entry never tags.
        with tempfile.TemporaryDirectory() as tmp:
            self.REGISTRY = HelperAnchorTests.REGISTRY.replace(
                "appeasement change on a lobby\n", "appeasement change on a lobby\n- stack: vanilla only\n")
            refs, mod, game = self._setup(tmp, {
                "events/a.txt": "a.1 = { option = { add_lobby_appeasement = { AMOUNT = 1 } } }\n",
            })
            self.assertTrue(refs[0].vanilla_stack_only)
            self.assertEqual(helper_anchor_warnings(refs, mod, game), [])

    def test_vanilla_only_stack_entry_still_warns_for_a_gui_use(self):
        # A .gui reading the helper leaves no frame in the error's stack.
        with tempfile.TemporaryDirectory() as tmp:
            self.REGISTRY = HelperAnchorTests.REGISTRY.replace(
                "appeasement change on a lobby\n", "appeasement change on a lobby\n- stack: vanilla only\n")
            refs, mod, game = self._setup(tmp, {
                "gui/panel.gui": "text = \"[ScriptValue('add_lobby_appeasement')]\"\n",
            })
            out = helper_anchor_warnings(refs, mod, game)
        self.assertEqual([w["mod_uses"] for w in out], [{"add_lobby_appeasement": ["gui/panel.gui:1"]}])

    def test_mod_only_anchor_warns_unless_reviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, mod, game = self._setup(tmp, {"common/ideologies/modified.txt": ""})
            doc = os.path.join(tmp, "docs", "vanilla", "vanilla_known_bugs.md")
            with open(doc, "a", encoding="utf-8") as f:
                f.write("\n### `common/ideologies/modified.txt` — replayed vanilla\n\n```\nError\n```\n"
                        "\n### `common/ideologies/modified.txt:2` — reviewed replay\n"
                        "- reviewed: mod anchor, the mod replays vanilla here\n\n```\nError\n```\n")
            _vanilla_bug_cache.clear()
            refs, _, _, _ = load_vanilla_bug_registry(doc)
            out = mod_only_anchor_warnings(refs, mod, game)
        self.assertEqual([(w["kind"], w["entry"], w["anchors"]) for w in out],
                         [("mod_only_anchor", "replayed vanilla", ["modified.txt"])])
        self.assertEqual(mod_only_anchor_warnings(refs, mod, None), [])

    def test_comments_and_definitions_are_not_uses(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, mod, game = self._setup(tmp, {
                "events/a.txt": "a.1 = {\n\t# add_lobby_appeasement = { AMOUNT = 1 }\n}\n",
                "common/scripted_effects/mod_copy.txt": "add_lobby_appeasement = { }\n",
            })
            self.assertEqual(helper_anchor_warnings(refs, mod, game), [])

    def test_gui_string_mention_is_a_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, mod, game = self._setup(tmp, {
                "gui/panel.gui": 'text = "#v [ScriptValue(\'add_lobby_appeasement\')]#!" # unused_effect\n',
            })
            out = helper_anchor_warnings(refs, mod, game)
        self.assertEqual([sorted(w["mod_uses"]) for w in out], [["add_lobby_appeasement"]])

    def test_mod_override_of_the_helper_file_supplies_the_definitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, mod, game = self._setup(tmp, {
                "common/scripted_effects/00_lobby_effects.txt": "mod_only_helper = { }\n",
                "events/a.txt": "a.1 = { immediate = { add_lobby_appeasement = { AMOUNT = 1 } mod_only_helper = yes } }\n",
            })
            out = helper_anchor_warnings(refs, mod, game)
        self.assertEqual([sorted(w["mod_uses"]) for w in out], [["mod_only_helper"]])

    def test_lists_at_most_five_uses_per_definition(self):
        calls = "".join(f"\t\tadd_lobby_appeasement = {{ AMOUNT = {i} }}\n" for i in range(8))
        with tempfile.TemporaryDirectory() as tmp:
            refs, mod, game = self._setup(tmp, {"events/a.txt": f"a.1 = {{\n\timmediate = {{\n{calls}\t}}\n}}\n"})
            out = helper_anchor_warnings(refs, mod, game)
        self.assertEqual(len(out[0]["mod_uses"]["add_lobby_appeasement"]), 5)
        self.assertIn("8 mentions", out[0]["detail"])

    def test_no_vanilla_files_no_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, mod, _ = self._setup(tmp, {"events/a.txt": "a.1 = { immediate = { add_lobby_appeasement = { AMOUNT = 1 } } }\n"})
            self.assertEqual(helper_anchor_warnings(refs, mod, None), [])

    def test_mod_uses_sees_an_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "events", "a.txt")
            os.makedirs(os.path.dirname(path))
            with open(path, "w", encoding="utf-8") as f:
                f.write("a.1 = { immediate = { x = yes } }\n")
            names = frozenset({"y"})
            self.assertEqual(mod_uses(tmp, names), {})
            with open(path, "w", encoding="utf-8") as f:
                f.write("a.1 = { immediate = { y = yes } }\n")
            os.utime(path, (time.time() + 10, time.time() + 10))
            self.assertEqual(mod_uses(tmp, names), {"y": ["events/a.txt:1"]})

    def test_live_registry_reviewed_lines_name_their_check(self):
        root = os.path.dirname(os.path.abspath(__file__))
        _vanilla_bug_cache.clear()
        refs, _, _, warnings = load_vanilla_bug_registry(os.path.join(root, "docs", "vanilla", "vanilla_known_bugs.md"))
        self.assertEqual(warnings, [])
        reviewed = [r for r in refs if r.reviewed]
        self.assertTrue(reviewed)
        for r in reviewed:
            for note in r.reviewed:
                self.assertTrue(note.startswith(("helper anchor, signature cannot match a mod call (",
                                                 "mod anchor, ", "mod frame, ")), note)


class LiveRegistryKeyReferenceTests(unittest.TestCase):
    """`Failed to read key reference` comes from one cpp line for a save load and
    for a script file's literal-key field; only the save load is noise. The
    registry's old signature, the message itself, filed #1194's `create_pop`
    load error as save noise (2026-10-27)."""

    SOURCE = "pdx_persistent_reader.cpp:268"

    def _tagged(self, message):
        root = os.path.dirname(os.path.abspath(__file__))
        _vanilla_bug_cache.clear()
        _, by_basename, by_source, _ = load_vanilla_bug_registry(
            os.path.join(root, "docs", "vanilla", "vanilla_known_bugs.md"))
        entry = LogEntry("20:19:29", self.SOURCE, message)
        tag_vanilla_bugs([entry], by_basename, by_source, mod_root=root)
        return entry.vanilla_bug_ref is not None

    def test_save_loads_are_tagged(self):
        self.assertTrue(self._tagged(
            'Error: "Failed to read key reference: superpower: superpower, near line: 1" in file: "" near line: 1'))
        self.assertTrue(self._tagged(
            'Error: "Failed to read key reference: headlines_all_minor_events: headlines_all_minor_events, '
            'near line: 42" in file: "save games/autosave_exit.v3" near line: 42'))

    def test_a_script_file_is_not(self):
        self.assertFalse(self._tagged(
            'Error: "Failed to read key reference: scope:sr_evac_culture: scope:sr_evac_culture, near line: 295\n'
            'Failed to read key reference: scope:sr_evac_religion: scope:sr_evac_religion, near line: 296" '
            'in file: "common/scripted_effects/sr_colony_autonomy_effects.txt" near line: 298'))


class WatchListTests(unittest.TestCase):
    """A `## Watch list` entry tags a line and never hides it: for a message
    that is usually vanilla's and can be the mod's, with nothing in the line
    to tell which. Its `- check:` line says what settles it."""

    DOC = (
        "## Engine noise (source-anchored)\n\n"
        "### `pdx_assert.cpp:641` — dead formation\n- source: `pdx_assert.cpp:641`\n\n"
        "```\nTrying to reposition a dead formation\n```\n\n"
        "## Watch list (tagged, never hidden)\n\n"
        "### `pdx_assert.cpp:641` — occupation data removed with a state\n"
        "- source: `pdx_assert.cpp:641`\n"
        "- check: read the same second for a mod effect in `common/scripted_effects/te_x.txt`\n\n"
        "```\nTrying to remove occupation data\n```\n"
    )

    def _load(self, tmp, doc=None):
        os.makedirs(os.path.join(tmp, "audits"), exist_ok=True)
        open(os.path.join(tmp, "audits", "open_issues.md"), "w", encoding="utf-8").close()
        os.makedirs(os.path.join(tmp, "vanilla"), exist_ok=True)
        path = os.path.join(tmp, "vanilla", "vanilla_known_bugs.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.DOC if doc is None else doc)
        _vanilla_bug_cache.clear()
        return load_vanilla_bug_registry(path)

    def _entries(self):
        return [
            LogEntry("18:21:24", "pdx_assert.cpp:641", "Assertion failed: Trying to reposition a dead formation"),
            LogEntry("18:21:29", "pdx_assert.cpp:641",
                     "Assertion failed: Trying to remove occupation data without returning the occupied provinces"),
            LogEntry("18:21:30", "pdx_assert.cpp:641", "Assertion failed: something new"),
        ]

    def test_a_watch_entry_tags_with_its_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            refs, by_basename, by_source, warnings = self._load(tmp)
            self.assertEqual(warnings, [])
            watch = [r for r in refs if r.kind == WATCH_KIND]
            self.assertEqual([r.title for r in watch], ["occupation data removed with a state"])
            # The path named in the check is advice, not an anchor.
            self.assertEqual(watch[0].file_basenames, [])
            entries = self._entries()
            tag_vanilla_bugs(entries, by_basename, by_source)
            self.assertEqual(entries[0].vanilla_bug_ref["kind"], "vanilla_noise")
            self.assertEqual(entries[1].vanilla_bug_ref["kind"], WATCH_KIND)
            self.assertIn("read the same second", entries[1].vanilla_bug_ref["check"])
            self.assertIsNone(entries[2].vanilla_bug_ref)

    def test_hide_keeps_a_watched_line_and_only_leaves_it_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, by_basename, by_source, _ = self._load(tmp)
            entries = self._entries()
            tag_vanilla_bugs(entries, by_basename, by_source)
            hidden = apply_known_noise_modes(entries, "hide", "hide")
            self.assertEqual([e.time for e in hidden], ["18:21:29", "18:21:30"])
            only = apply_known_noise_modes(entries, "only", "show")
            self.assertEqual([e.time for e in only], ["18:21:24"])
            self.assertEqual(len(apply_known_noise_modes(entries, "show", "show")), 3)

    def test_a_watch_entry_needs_a_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = self.DOC.replace(
                "- check: read the same second for a mod effect in `common/scripted_effects/te_x.txt`\n", "")
            _, _, _, warnings = self._load(tmp, doc)
            self.assertTrue(any("no `- check:` line" in w for w in warnings), warnings)

    def test_mod_noise_modes_are_unchanged(self):
        e = LogEntry("00:00:01", "x.cpp:1", "tracked")
        e.vanilla_bug_ref = {"title": "t", "kind": "mod_low_priority"}
        plain = LogEntry("00:00:02", "x.cpp:1", "new")
        self.assertEqual(apply_known_noise_modes([e, plain], "hide", "show"), [e, plain])
        self.assertEqual(apply_known_noise_modes([e, plain], "hide", "hide"), [plain])
        self.assertEqual(apply_known_noise_modes([e, plain], "show", "only"), [e])

    def test_the_live_watch_list_parses(self):
        root = os.path.dirname(os.path.abspath(__file__))
        _vanilla_bug_cache.clear()
        refs, _, _, warnings = load_vanilla_bug_registry(
            os.path.join(root, "docs", "vanilla", "vanilla_known_bugs.md"))
        watch = [r for r in refs if r.kind == WATCH_KIND]
        self.assertGreaterEqual(len(watch), 3)
        for ref in watch:
            self.assertTrue(ref.check, ref.title)
            self.assertTrue(ref.signatures, ref.title)
        self.assertFalse([w for w in warnings if "watch list" in w], warnings)


if __name__ == "__main__":
    unittest.main()
