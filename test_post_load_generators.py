"""Smoke test for the mod_state_server post-load generator registry.

For each module in POST_LOAD_GENERATORS, verifies that:
  1. The module is importable.
  2. It exposes a callable `regenerate` symbol.

Does NOT call regenerate() — that would require a fully loaded ModState and
several minutes of vanilla parsing. The integration check happens implicitly
when the server starts and logs `[post-load] <name> ok`.

Run: python test_post_load_generators.py
"""

import importlib
import sys
import unittest

from mod_state_server import POST_LOAD_GENERATORS


class PostLoadGeneratorSmokeTest(unittest.TestCase):
    def test_each_module_is_importable_and_exposes_regenerate(self):
        failures = []
        for label, module_name in POST_LOAD_GENERATORS:
            try:
                mod = importlib.import_module(module_name)
            except Exception as e:
                failures.append(f"{label}: import failed — {type(e).__name__}: {e}")
                continue
            fn = getattr(mod, "regenerate", None)
            if not callable(fn):
                failures.append(f"{label}: module {module_name} has no callable `regenerate`")
        if failures:
            self.fail(
                "POST_LOAD_GENERATORS contract violated:\n  " + "\n  ".join(failures)
            )


if __name__ == "__main__":
    unittest.main()
