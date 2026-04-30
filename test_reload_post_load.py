"""Integration tests for the mod_state_server post-load batch.

Requires the server running on http://127.0.0.1:8950. Each test snapshots the
log's `[post-load]` line count, hits a /reload endpoint, then asserts the
expected number of new lines appeared.

Run: .venv/bin/python -m unittest test_reload_post_load
"""

import time
import unittest
import urllib.error
import urllib.request

from mod_state_server import POST_LOAD_GENERATORS
from path_constants import mod_path

SERVER = "http://127.0.0.1:8950"
LOG_PATH = f"{mod_path}/mod_state_server.log"


def _server_running() -> bool:
    try:
        with urllib.request.urlopen(f"{SERVER}/status", timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def _count_post_load_lines() -> int:
    try:
        with open(LOG_PATH, "r") as f:
            return sum(1 for line in f if "[post-load]" in line)
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
