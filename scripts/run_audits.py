#!/usr/bin/env python3
"""Run the CI audits in parallel and explain any that fail.

    python3 scripts/run_audits.py                 # every audit CI runs
    python3 scripts/run_audits.py prev_scope ...  # some, by name (`_audit` optional)
    python3 scripts/run_audits.py --list

The roster, each audit's arguments and its suppression comment come from
`audit_registry.py`. A passing audit prints one line. A failing one prints its
own output, then what the flag means and the comment that suppresses an
intended one, so nobody has to look the placement up.

Needs no game. The audits run with CI's dummy `VIC3_*` paths even on a machine
that has the game, so the answer here is the answer CI gives; `--real-paths`
uses the machine's own.
Exit code: 0 when every audit passed, 1 otherwise.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import audit_registry  # noqa: E402

# path_constants resolves lazily, so these only need to be set, not real.
DUMMY_ENV = {
    "VIC3_BASE_GAME": "/nonexistent/game",
    "VIC3_MOD_DEPLOY_TARGET": "/nonexistent/deploy",
    "VIC3_VANILLA_REPO": "/nonexistent/vic3",
    "VIC3_VANILLA_DOCS_RUNTIME": "/nonexistent/docs",
    "VIC3_GAME_LOGS": "/nonexistent/logs",
}

IN_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"


def child_env(real_paths: bool = False) -> dict:
    """The environment a check runs in. By default the game paths are CI's
    dummies, whatever this machine has configured, so a check answers here as
    it will in CI: with a real install several audits read vanilla's files and
    report differently (#1271, #1349). `real_paths` leaves the machine's own
    paths alone, falling back to the dummies only where nothing is configured.
    """
    env = dict(os.environ)
    if not real_paths:
        env.update(DUMMY_ENV)
    elif not os.path.exists(os.path.join(REPO_ROOT, "paths.local.json")):
        for key, value in DUMMY_ENV.items():
            env.setdefault(key, value)
    if not real_paths:
        # CI has no PYTHONPATH. On the owner's machine it carries a ROS install
        # whose pytest plugin crashes collection before any test runs.
        env.pop("PYTHONPATH", None)
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def resolve(names):
    """Registry entries for the given names, in registry order. Raises
    SystemExit on an unknown name or one CI doesn't run."""
    if not names:
        return list(audit_registry.ci_audits())
    wanted = []
    for raw in names:
        stem = raw[:-3] if raw.endswith(".py") else raw
        name = stem if stem.endswith("_audit") else stem + "_audit"
        audit = audit_registry.BY_NAME.get(name)
        if audit is None:
            raise SystemExit(f"No audit named {name}. `--list` shows them.")
        if audit.ci is None:
            raise SystemExit(
                f"{name} has no exit-code mode; it runs on a server reload only "
                "(POST /reload, then read the response's `warnings`)."
            )
        wanted.append(audit)
    return wanted


def run_one(audit, env):
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, f"{audit.name}.py", *audit.ci],
        cwd=REPO_ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return audit, proc.returncode, proc.stdout, time.monotonic() - started


def report_failure(audit, output, tail_lines):
    lines = output.rstrip().splitlines()
    shown = lines if tail_lines <= 0 else lines[-tail_lines:]
    if IN_ACTIONS:
        print(f"::group::{audit.name} output")
    if len(shown) < len(lines):
        print(f"  ... ({len(lines) - len(shown)} earlier lines; run `{audit.command}` to see them)")
    for line in shown:
        print("  " + line)
    if IN_ACTIONS:
        print("::endgroup::")
    print()
    for line in audit_registry.suppression_hint(audit.name).splitlines():
        print("  " + line)
    print(f"  Reproduce: {audit.command}")
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="Audits to run (default: every CI audit).")
    parser.add_argument("--list", action="store_true", help="List the CI audits and exit.")
    parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 2)
    parser.add_argument(
        "--tail", type=int, default=60,
        help="Lines of a failing audit's output to show (0: all). Default 60.",
    )
    parser.add_argument(
        "--real-paths", action="store_true",
        help="Use this machine's game paths instead of CI's dummy ones.",
    )
    args = parser.parse_args(argv)

    audits = resolve(args.names)
    if args.list:
        for audit in audits:
            print(audit.command)
        return 0

    env = child_env(args.real_paths)
    started = time.monotonic()
    failed = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for audit, code, output, seconds in pool.map(lambda a: run_one(a, env), audits):
            if code == 0:
                print(f"ok    {audit.name}  ({seconds:.1f}s)")
                continue
            failed.append(audit)
            if IN_ACTIONS:
                print(f"::error title={audit.name}::{audit.name} failed (exit {code}). {audit.catches}")
            print(f"FAIL  {audit.name}  (exit {code}, {seconds:.1f}s)")
            report_failure(audit, output, args.tail)

    total = time.monotonic() - started
    if failed:
        print(f"{len(failed)} of {len(audits)} audits failed in {total:.0f}s: "
              + ", ".join(a.name for a in failed))
        print("What each audit catches and where its comment goes: docs/guides/audits.md")
        return 1
    print(f"All {len(audits)} audits passed in {total:.0f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
