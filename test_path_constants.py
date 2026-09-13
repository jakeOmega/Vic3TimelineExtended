"""Unit tests for the lazy path resolution in path_constants.py.

Pure unit — no live game files, no server. Run:
    python3 -m unittest test_path_constants -v
"""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import path_constants as pc


REPO_ROOT = Path(__file__).resolve().parent

LAZY_NAMES = (
    "base_game_path",
    "mod_deploy_target",
    "vanilla_snapshot_docs_path",
    "vanilla_source_repo_path",
    "vanilla_docs_path",
    "mod_loaded_docs_path",
    "game_logs_path",
    "vic3_modding_digests_path",
    "vanilla_snapshot_docs_path_default",
)


@contextlib.contextmanager
def isolated(env: dict | None = None):
    """Run the body with no paths.local.json, no autodetection, no cached
    values and only the given VIC3_* env vars visible."""
    cached = {name: pc.__dict__[name] for name in LAZY_NAMES if name in pc.__dict__}
    patched_env = {k: v for k, v in os.environ.items() if not k.startswith("VIC3_")}
    patched_env.update(env or {})
    try:
        with mock.patch.dict(pc._LOCAL_CFG, {}, clear=True), mock.patch.object(
            pc, "_AUTODETECTED", {}
        ), mock.patch.dict(os.environ, patched_env, clear=True):
            for name in LAZY_NAMES:
                pc.__dict__.pop(name, None)
            yield
    finally:
        for name in LAZY_NAMES:
            pc.__dict__.pop(name, None)
        pc.__dict__.update(cached)


class EagerConstantsTest(unittest.TestCase):
    def test_repo_paths_resolve_at_import(self):
        self.assertIn("mod_path", vars(pc))
        self.assertIn("doc_path", vars(pc))
        self.assertEqual(pc.mod_path, str(REPO_ROOT))

    def test_import_needs_no_game_install(self):
        """`import path_constants` must not touch a per-machine path."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("VIC3_")}
        proc = subprocess.run(
            [sys.executable, "-c", "import path_constants; print(path_constants.mod_path)"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), str(REPO_ROOT))


class LazyResolutionTest(unittest.TestCase):
    def test_env_var_wins_and_value_is_cached(self):
        with isolated({"VIC3_BASE_GAME": "/tmp/base-game"}):
            self.assertNotIn("base_game_path", vars(pc))
            self.assertEqual(pc.base_game_path, "/tmp/base-game")
            # Cached in module globals, so a later env change is not re-read.
            self.assertIn("base_game_path", vars(pc))
            os.environ["VIC3_BASE_GAME"] = "/tmp/changed"
            self.assertEqual(pc.base_game_path, "/tmp/base-game")

    def test_local_config_is_used_when_env_is_absent(self):
        with isolated():
            pc._LOCAL_CFG["game_logs_path"] = "/tmp/logs-from-config"
            self.assertEqual(pc.game_logs_path, "/tmp/logs-from-config")

    def test_alias_tracks_its_target(self):
        with isolated({"VIC3_VANILLA_DOCS_RUNTIME": "/tmp/docs"}):
            self.assertEqual(pc.mod_loaded_docs_path, "/tmp/docs")
            self.assertEqual(pc.mod_loaded_docs_path, pc.vanilla_docs_path)

    def test_optional_constant_returns_none(self):
        with isolated():
            self.assertIsNone(pc.vic3_modding_digests_path)
            self.assertIsNone(pc.vanilla_snapshot_docs_path)
            self.assertIsNone(pc.vanilla_snapshot_docs_path_default)

    def test_unresolved_required_path_raises_setup_hint(self):
        with isolated():
            with self.assertRaises(RuntimeError) as ctx:
                pc.base_game_path
            message = str(ctx.exception)
            self.assertIn("base_game_path", message)
            self.assertIn("$VIC3_BASE_GAME", message)
            self.assertIn("python3 scripts/setup.py", message)

    def test_from_import_still_works(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("VIC3_")}
        env["VIC3_MOD_DEPLOY_TARGET"] = "/tmp/deploy"
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "from path_constants import mod_deploy_target; print(mod_deploy_target)",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "/tmp/deploy")

    def test_unknown_attribute_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            pc.not_a_path_constant

    def test_all_covers_the_eager_and_lazy_names(self):
        self.assertEqual(set(pc.__all__), {"mod_path", "doc_path", *LAZY_NAMES})

    def test_star_import_exports_lazy_constants(self):
        """`import *` only sees the lazy names because __all__ names them."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("VIC3_")}
        env.update(
            VIC3_BASE_GAME="/tmp/base-game",
            VIC3_MOD_DEPLOY_TARGET="/tmp/deploy",
            VIC3_VANILLA_REPO="/tmp/vanilla",
            VIC3_VANILLA_DOCS_RUNTIME="/tmp/docs",
            VIC3_GAME_LOGS="/tmp/logs",
        )
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "from path_constants import *; print(base_game_path)",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "/tmp/base-game")

    def test_dir_lists_the_lazy_names(self):
        listed = dir(pc)
        for name in LAZY_NAMES:
            self.assertIn(name, listed)
        self.assertIn("mod_path", listed)


if __name__ == "__main__":
    unittest.main()
