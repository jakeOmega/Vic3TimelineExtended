"""Backwards-compat shim — superseded by ../engine_docs_render.py.

The original 588-line generator was migrated into a library that the mod
state server invokes on `/reload`. Run `python -m engine_docs_render` (or
`python engine_docs_render.py`) from the repo root to regenerate the
reference files standalone.

This module forwards to the new entry point so existing scripts that import
or invoke the old name keep working.
"""
import os
import sys

# Make sure repo root is on sys.path so `import engine_docs_render` resolves
# even when this script is run as docs/parse_triggers_effects.py directly.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from engine_docs_render import _cli  # noqa: E402

if __name__ == "__main__":
    _cli()
