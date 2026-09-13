"""Integration tests for the mod_state_server post-load batch.

The HTTP tests require the server running on http://127.0.0.1:8950: each
snapshots the log's per-generator `[post-load]` line count, hits a /reload
endpoint, then asserts the expected number of new lines appeared. The #242
tests below it are pure-Python and always run.

Run: .venv/bin/python -m unittest test_reload_post_load
"""

import re
import time
import unittest
import urllib.error
import urllib.request

from mod_state_server import POST_LOAD_GENERATORS
from path_constants import mod_path

SERVER = "http://127.0.0.1:8950"
LOG_PATH = f"{mod_path}/mod_state_server.log"

# One line per generator: `ok`, a `surfaced issues:` finding, or a `FAILED`
# crash. Deliberately narrower than a plain `[post-load]` substring so the
# chain's other bookkeeping lines (the re-parse after generator writes, the
# closing "N post-load step(s)" summary) don't inflate the count.
_PER_GENERATOR_LINE = re.compile(
    r"\[post-load(?: WARN)?\] \S+ (?:ok \(|FAILED|surfaced issues:)"
)


def _server_running() -> bool:
    try:
        with urllib.request.urlopen(f"{SERVER}/status", timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def _count_post_load_lines() -> int:
    try:
        with open(LOG_PATH, "r") as f:
            return sum(1 for line in f if _PER_GENERATOR_LINE.search(line))
    except FileNotFoundError:
        return 0


def _post_reload(query: str = "") -> None:
    url = f"{SERVER}/reload" + (f"?{query}" if query else "")
    req = urllib.request.Request(url, method="POST")
    # The server runs _load_mod_state synchronously inside the handler;
    # generous timeout for vanilla 1.13 (~110s parse + post-load).
    with urllib.request.urlopen(req, timeout=300) as r:
        assert r.status == 200, f"reload returned {r.status}"


@unittest.skipUnless(_server_running(), "mod_state_server not running on :8950")
class ReloadPostLoadTest(unittest.TestCase):
    def test_full_reload_runs_every_generator(self):
        before = _count_post_load_lines()
        _post_reload()
        # Give the file handler a moment to flush
        time.sleep(0.5)
        after = _count_post_load_lines()
        new_lines = after - before
        self.assertEqual(
            new_lines,
            len(POST_LOAD_GENERATORS),
            f"expected {len(POST_LOAD_GENERATORS)} new [post-load] lines after "
            f"/reload, got {new_lines}",
        )

    def test_engine_only_reload_skips_post_load(self):
        before = _count_post_load_lines()
        _post_reload("engine_only=true")
        time.sleep(0.5)
        after = _count_post_load_lines()
        self.assertEqual(
            after,
            before,
            f"expected NO new [post-load] lines after engine_only=true reload, "
            f"got {after - before}",
        )


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# #242 — crashing generators/audits must reach the reload `warnings` array,
# writers that run after the parse must be reported (and trigger one re-parse),
# and ModState parse failures must be visible in /status.
#
# These are pure-Python: they drive the post-load chain with stub modules and a
# stub ModState, so they run without the game or a live server.
# ---------------------------------------------------------------------------
import logging
import os
import sys
import tempfile
import types
from unittest import mock

import mod_state_server as mss


class _FakeModState:
    """Minimal stand-in for ModState: records re-parse calls."""

    def __init__(self):
        self.reload_calls = 0
        self.localization = {}
        self._reverse_loc = None
        self.parse_failures = []

    def reload_mod(self, mod_paths):
        self.reload_calls += 1

    def add_localization(self, loc_path):
        pass


_NO_REGENERATE = object()


class _QuietServerLogMixin(unittest.TestCase):
    """Keep the server logger's console output (including deliberate
    tracebacks) out of the test run."""

    def setUp(self):
        super().setUp()
        for logger in (mss.logger, logging.getLogger("mod_state")):
            previous = logger.level
            logger.setLevel(logging.CRITICAL + 1)
            self.addCleanup(logger.setLevel, previous)


class _PostLoadChainTestBase(_QuietServerLogMixin):
    def setUp(self):
        super().setUp()
        # The chain is a no-op when the skip env var is set; make sure a
        # developer's exported flag can't silently pass these tests.
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop("VIC3_SKIP_POST_LOAD_GENERATORS", None)
        self.addCleanup(env.stop)

    def _install_module(self, name, regenerate=_NO_REGENERATE):
        """Register a stub module in sys.modules for importlib to find.
        Pass regenerate=_NO_REGENERATE (the default) or None for a module that
        violates the contract by not exposing one."""
        module = types.ModuleType(name)
        if regenerate is not _NO_REGENERATE and regenerate is not None:
            module.regenerate = regenerate
        sys.modules[name] = module
        self.addCleanup(sys.modules.pop, name, None)
        return module

    def _run(self, regenerators, audits, mod_state=None, **kwargs):
        state = mod_state or _FakeModState()
        with mock.patch.object(mss, "POST_LOAD_REGENERATORS", regenerators), \
                mock.patch.object(mss, "POST_LOAD_AUDITS", audits):
            mss._run_post_load_generators(state, **kwargs)
        return state


class PostLoadFailureWarningTests(_PostLoadChainTestBase):
    def test_raising_regenerate_becomes_a_warning(self):
        def _boom(mod_state=None):
            raise RuntimeError("audit exploded")

        self._install_module("fake_exploding_audit", _boom)
        self._run([], [("exploding_audit", "fake_exploding_audit")], audits_only=True)

        self.assertEqual(len(mss._post_load_warnings), 1)
        warning = mss._post_load_warnings[0]
        self.assertEqual(warning["label"], "exploding_audit")
        self.assertEqual(warning["module"], "fake_exploding_audit")
        self.assertEqual(warning["error"], "RuntimeError: audit exploded")
        self.assertIn("audit exploded", warning["traceback_tail"])

    def test_missing_regenerate_attribute_becomes_a_warning(self):
        self._install_module("fake_contractless_audit", None)
        self._run([], [("contractless", "fake_contractless_audit")], audits_only=True)

        self.assertEqual(len(mss._post_load_warnings), 1)
        warning = mss._post_load_warnings[0]
        self.assertEqual(warning["label"], "contractless")
        self.assertIn("regenerate", warning["error"])
        self.assertTrue(warning["error"].startswith("AttributeError:"))

    def test_import_error_becomes_a_warning(self):
        self._run([], [("no_such", "fake_module_that_does_not_exist")], audits_only=True)

        self.assertEqual(len(mss._post_load_warnings), 1)
        self.assertTrue(
            mss._post_load_warnings[0]["error"].startswith("ModuleNotFoundError:"),
            mss._post_load_warnings[0]["error"],
        )

    def test_one_failure_does_not_stop_the_chain(self):
        ran = []

        def _boom(mod_state=None):
            raise ValueError("nope")

        self._install_module("fake_boom_audit", _boom)
        self._install_module("fake_ok_audit", lambda mod_state=None: ran.append("ok"))
        self._run(
            [],
            [("boom", "fake_boom_audit"), ("ok", "fake_ok_audit")],
            audits_only=True,
        )

        self.assertEqual(ran, ["ok"])
        self.assertEqual([w["label"] for w in mss._post_load_warnings], ["boom"])


class PostLoadWriterDetectionTests(_PostLoadChainTestBase):
    def setUp(self):
        super().setUp()
        self.root = tempfile.mkdtemp()
        target_dir = os.path.join(self.root, "common", "ideologies")
        os.makedirs(target_dir)
        self.target = os.path.join(target_dir, "modified.txt")
        with open(self.target, "w", encoding="utf-8") as f:
            f.write("original = yes\n")
        patch_root = mock.patch.object(mss, "mod_path", self.root)
        patch_root.start()
        self.addCleanup(patch_root.stop)
        patch_paths = mock.patch.object(mss, "mod_paths", {})
        patch_paths.start()
        self.addCleanup(patch_paths.stop)

    def _write(self, text):
        def _regenerate(mod_state=None):
            with open(self.target, "w", encoding="utf-8") as f:
                f.write(text)
        return _regenerate

    def test_snapshot_diff_detects_content_change(self):
        before = mss._snapshot_mod_text_files(self.root)
        self.assertIn("common/ideologies/modified.txt", before)
        with open(self.target, "w", encoding="utf-8") as f:
            f.write("regenerated = yes\n")
        after = mss._snapshot_mod_text_files(self.root)
        self.assertEqual(
            mss._changed_files(before, after), ["common/ideologies/modified.txt"]
        )

    def test_writer_is_reported_and_triggers_one_reparse(self):
        self._install_module("fake_writer", self._write("regenerated = yes\n"))
        state = self._run([("writer", "fake_writer")], [])

        self.assertEqual(mss._post_load_wrote_files, ["common/ideologies/modified.txt"])
        self.assertTrue(mss._post_load_reparsed)
        # Bounded: exactly one re-parse, never a loop.
        self.assertEqual(state.reload_calls, 1)
        self.assertEqual(mss._post_load_warnings, [])

    def test_audits_run_after_the_reparse(self):
        order = []

        def _writer(mod_state=None):
            order.append("write")
            with open(self.target, "w", encoding="utf-8") as f:
                f.write("regenerated = yes\n")

        self._install_module("fake_writer_ordered", _writer)
        self._install_module("fake_audit_ordered", lambda mod_state=None: order.append("audit"))

        class _OrderedState(_FakeModState):
            def reload_mod(self, mod_paths):
                order.append("reparse")
                super().reload_mod(mod_paths)

        self._run(
            [("writer", "fake_writer_ordered")],
            [("audit", "fake_audit_ordered")],
            mod_state=_OrderedState(),
        )
        self.assertEqual(order, ["write", "reparse", "audit"])

    def test_identical_rewrite_is_not_reported_as_a_write(self):
        # Several generators rewrite their output file unconditionally; only a
        # real content change should cost a re-parse.
        self._install_module("fake_idempotent_writer", self._write("original = yes\n"))
        state = self._run([("writer", "fake_idempotent_writer")], [])

        self.assertEqual(mss._post_load_wrote_files, [])
        self.assertFalse(mss._post_load_reparsed)
        self.assertEqual(state.reload_calls, 0)

    def test_failed_reparse_is_recorded_as_a_warning(self):
        self._install_module("fake_writer_failing_reparse", self._write("regenerated = yes\n"))

        class _BrokenState(_FakeModState):
            def reload_mod(self, mod_paths):
                raise OSError("disk gone")

        self._run([("writer", "fake_writer_failing_reparse")], [], mod_state=_BrokenState())

        self.assertEqual(mss._post_load_wrote_files, ["common/ideologies/modified.txt"])
        self.assertFalse(mss._post_load_reparsed)
        self.assertEqual(
            [w["label"] for w in mss._post_load_warnings], ["post_load_reparse"]
        )
        self.assertEqual(mss._post_load_warnings[0]["error"], "OSError: disk gone")

    def test_audits_only_never_snapshots_or_reparses(self):
        self._install_module("fake_audit_only", lambda mod_state=None: None)
        state = self._run(
            [("writer", "fake_writer_never_run")],
            [("audit", "fake_audit_only")],
            audits_only=True,
        )
        self.assertEqual(mss._post_load_wrote_files, [])
        self.assertEqual(state.reload_calls, 0)
        self.assertEqual(mss._post_load_warnings, [])


class EngineOnlyReloadWarningTests(_QuietServerLogMixin):
    def test_engine_docs_failure_is_returned_as_a_warning(self):
        def _boom():
            raise RuntimeError("engine docs missing")

        with mock.patch.object(mss, "_load_engine_docs", _boom), \
                mock.patch.object(mss, "_validate_engine_coverage", return_value={"summary": {}}), \
                mock.patch.object(mss, "_render_engine_coverage_md", return_value=""), \
                mock.patch("builtins.open", mock.mock_open()):
            warnings = mss._reload_engine_only()

        self.assertEqual([w["label"] for w in warnings], ["engine_docs"])
        self.assertEqual(warnings[0]["error"], "RuntimeError: engine docs missing")
        self.assertIn("engine docs missing", warnings[0]["traceback_tail"])

    def test_validation_failure_is_returned_as_a_warning(self):
        def _boom():
            raise ValueError("coverage blew up")

        with mock.patch.object(mss, "_load_engine_docs", lambda: None), \
                mock.patch.object(mss, "_validate_engine_coverage", _boom):
            warnings = mss._reload_engine_only()

        self.assertEqual([w["label"] for w in warnings], ["engine_coverage_validation"])
        self.assertEqual(warnings[0]["error"], "ValueError: coverage blew up")

    def test_clean_engine_only_reload_returns_no_warnings(self):
        with mock.patch.object(mss, "_load_engine_docs", lambda: None), \
                mock.patch.object(mss, "_validate_engine_coverage", return_value={"summary": {}}), \
                mock.patch.object(mss, "_render_engine_coverage_md", return_value=""), \
                mock.patch("builtins.open", mock.mock_open()):
            self.assertEqual(mss._reload_engine_only(), [])


class ParseFailureTests(_QuietServerLogMixin):
    """#242 §3 — parse failures are collected on ModState and shown in /status."""

    def _mod_state_with_broken_file(self):
        from mod_state import ModState

        root = tempfile.mkdtemp()
        with open(os.path.join(root, "broken.txt"), "wb") as f:
            # Invalid UTF-8: fails at read time regardless of parser semantics.
            f.write(b"foo = { bar = \xff\xfe }\n")
        return ModState({}, {"Test": root}), root

    def test_parse_failure_is_collected_not_printed(self):
        with self.assertLogs("mod_state", level="WARNING") as captured:
            state, root = self._mod_state_with_broken_file()
        self.assertTrue(any("broken.txt" in line for line in captured.output))
        self.assertEqual(len(state.parse_failures), 1)
        failure = state.parse_failures[0]
        self.assertEqual(failure["file"], os.path.join(root, "broken.txt"))
        self.assertTrue(failure["error"].startswith("UnicodeDecodeError:"))
        self.assertEqual(failure["source"], "mod")

    def test_reload_mod_clears_stale_mod_failures(self):
        state, root = self._mod_state_with_broken_file()
        state.parse_failures.append(
            {"file": "/vanilla/x.txt", "error": "ValueError: v", "source": "vanilla"}
        )
        os.remove(os.path.join(root, "broken.txt"))
        state.reload_mod({"Test": root})
        self.assertEqual(
            state.parse_failures,
            [{"file": "/vanilla/x.txt", "error": "ValueError: v", "source": "vanilla"}],
        )

    def test_status_exposes_parse_failures(self):
        state, _ = self._mod_state_with_broken_file()
        with mock.patch.object(mss, "_vanilla_data_loaded", return_value=True), \
                mock.patch.object(mss, "ms", state):
            status = mss.ModStateHandler._status(None)
        self.assertEqual(status["parse_failure_count"], 1)
        self.assertTrue(status["parse_failures"][0]["error"].startswith("UnicodeDecodeError:"))
