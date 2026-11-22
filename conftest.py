"""pytest setup for the whole suite: dummy game paths where the machine has none.

Ten test modules import `mod_state_server`, which resolves the per-machine
paths (`path_constants`). No test reads the game through them, so on a machine
with no Victoria 3 install any value will do; without one the run dies at
collection with "Could not resolve path 'base_game_path'". CI sets the same
dummies in its workflow.

A machine that has `paths.local.json` (written by `scripts/setup.py`), or has
the variables set already, is left alone. `python3 -m unittest` does not read
this file: set the variables yourself there, or use `scripts/preflight.py`.
"""
import os

import pytest

_DUMMY_ENV = {
    "VIC3_BASE_GAME": "/nonexistent/game",
    "VIC3_MOD_DEPLOY_TARGET": "/nonexistent/deploy",
    "VIC3_VANILLA_REPO": "/nonexistent/vic3",
    "VIC3_VANILLA_DOCS_RUNTIME": "/nonexistent/docs",
    "VIC3_GAME_LOGS": "/nonexistent/logs",
}

if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "paths.local.json")):
    for _key, _value in _DUMMY_ENV.items():
        os.environ.setdefault(_key, _value)


@pytest.fixture(autouse=True)
def _no_real_powershell_for_crash_reporters(request):
    """No game_qa test may reach the real PowerShell through `game_qa.crash_reporter` (#1905). On a machine with
    paths.local.json, `base_game_path` is the real install, whose crash reporter exists, so a test that ran a
    restore without faking the listing would list, and could end, a real CrashReporter process. Every call goes
    through `crash_reporter._run`; here it is refused, and the test fails at teardown if anything tried. A test
    hands `list_reporters` or `close` a `run` of its own, or patches them, instead."""
    path = getattr(request.node, "path", None)
    if path is None or not path.name.startswith("test_game_qa_"):
        yield
        return
    from game_qa import crash_reporter

    calls = []

    def refused(argv, *args, **kwargs):
        calls.append(list(argv)[:3])
        raise OSError("conftest.py: a test reached the real PowerShell through game_qa.crash_reporter")

    original, crash_reporter._run = crash_reporter._run, refused
    try:
        yield
    finally:
        crash_reporter._run = original
    assert not calls, "the test reached the real PowerShell through game_qa.crash_reporter: %r" % calls
