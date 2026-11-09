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
