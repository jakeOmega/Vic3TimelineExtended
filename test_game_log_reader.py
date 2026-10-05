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
    filter_debug_log,
    filter_entries,
    dedupe,
    diff_against_backup,
    cluster_sessions,
    summarize,
    render_error_log_digest,
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
    mod_uses,
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

    def test_live_registry_reviewed_lines_name_the_helper_anchor(self):
        root = os.path.dirname(os.path.abspath(__file__))
        _vanilla_bug_cache.clear()
        refs, _, _, warnings = load_vanilla_bug_registry(os.path.join(root, "docs", "vanilla", "vanilla_known_bugs.md"))
        self.assertEqual(warnings, [])
        reviewed = [r for r in refs if r.reviewed]
        self.assertTrue(reviewed)
        for r in reviewed:
            for note in r.reviewed:
                self.assertTrue(note.startswith("helper anchor, signature cannot match a mod call ("), note)


if __name__ == "__main__":
    unittest.main()
