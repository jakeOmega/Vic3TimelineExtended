#!/usr/bin/env python3
"""Run what CI runs, before you push.

    .venv/bin/python scripts/preflight.py             # every check of CI's main job
    .venv/bin/python scripts/preflight.py --quick     # all of it but the test suite
    .venv/bin/python scripts/preflight.py --changed   # only what your diff can affect
    .venv/bin/python scripts/preflight.py --only audits docs
    .venv/bin/python scripts/preflight.py --list

This file is the one list of CI's game-independent checks: the workflow
(`.github/workflows/ci.yml`) runs `preflight.py --ci --only <group>` once per
group, so a check added to `CHECKS` below runs in CI and here alike, and a
green preflight means a green main job. (The texture-dimension job is separate:
it needs `gfx/`.)

Checks run with CI's dummy game paths even on a machine with the game, so the
result here is CI's result; `--real-paths` uses the machine's own. Use the
venv's Python: the system one lacks numpy, pytest and ruff.

`--changed` is for the loop while you work, not the gate before a push. It
compares the branch and working tree with `origin/main` and drops groups the
diff cannot reach, and narrows the test run only when no mod content changed.

Exit code: 0 when every check that ran passed, 1 otherwise.
"""
from __future__ import annotations

import argparse
import fnmatch
import io
import os
import subprocess
import sys
import time
import tokenize
from dataclasses import dataclass, field
from typing import Callable

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import run_audits  # noqa: E402

PY = sys.executable

# Generator-owned files whose generator re-emits unformatted text, so
# normalizing them would be undone by the next reload (PR #272).
TAB_CHECK_PATHSPECS = (
    ":(glob)common/**/*.txt",
    ":(glob)events/**/*.txt",
    ":!:common/ideologies/modified.txt",
    ":!:common/scripted_effects/extra_law_consistency_generated.txt",
)

# Docs kept in CRLF. A Python rewrite without newline="" flips one to LF and
# turns a two-line edit into a thousand-line diff.
CRLF_DOCS = (
    "docs/systems/journal_entry_systems.md",
    "docs/guides/gui_modding_guide.md",
    "docs/vanilla/treaty_articles_reference.md",
    "docs/vanilla/wonder_buildings_reference.md",
)

MOD_CONTENT = ("common/*", "events/*", "localization/*", "gui/*", "map_data/*", ".metadata/*")
PYTHON = ("*.py",)
DOCS = ("docs/*", "*.md")


@dataclass
class Ctx:
    env: dict
    ci: bool
    changed: list | None
    """Changed paths under --changed, else None (run everything)."""


@dataclass
class Result:
    ok: bool
    output: str = ""
    skipped: str = ""


@dataclass
class Check:
    id: str
    group: str
    title: str
    run: Callable[[Ctx], Result]
    triggers: tuple = ()
    """Path globs. Under --changed the check runs when a changed path matches
    one. Empty: always runs."""
    fix: str = ""
    """What to do when it fails."""
    slow: bool = False
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- helpers

def sh(ctx: Ctx, argv, **kwargs) -> Result:
    """Run a command. In CI its output streams into the log as it comes; locally
    it is captured and shown only if the check fails."""
    if ctx.ci:
        code = subprocess.run(argv, cwd=REPO_ROOT, env=ctx.env, **kwargs).returncode
        return Result(code == 0)
    proc = subprocess.run(
        argv, cwd=REPO_ROOT, env=ctx.env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs,
    )
    return Result(proc.returncode == 0, proc.stdout)


def command(*argv) -> Callable[[Ctx], Result]:
    return lambda ctx: sh(ctx, list(argv))


def git(*argv) -> str:
    return subprocess.run(
        ["git", *argv], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    ).stdout


def matches(path: str, globs) -> bool:
    return any(fnmatch.fnmatch(path, g) for g in globs)


def changed_paths(base: str) -> list:
    """Paths that differ from the merge base with `base`, committed or not, plus
    untracked files."""
    merge_base = git("merge-base", "HEAD", base).strip()
    if not merge_base:
        raise SystemExit(
            f"--changed: no merge base with {base}. Fetch it (`git fetch origin main`) "
            "or pass --base <ref>."
        )
    paths = set(git("diff", "--name-only", merge_base).split("\n"))
    paths |= set(git("ls-files", "--others", "--exclude-standard").split("\n"))
    paths.discard("")
    return sorted(paths)


# --------------------------------------------------------------------------- checks

def check_py311_fstrings(ctx: Ctx) -> Result:
    """CI also runs Python 3.11, which rejects what 3.12 allows inside an
    f-string's braces (PEP 701): the string's own quote, a backslash, a comment.
    3.12's compileall can't see it, so scan the tokens."""
    if sys.version_info < (3, 12):
        return Result(True, skipped="this Python is 3.11: compileall already rejects them")
    files = git("ls-files", "*.py").split("\n")
    if ctx.changed is not None:
        files = [f for f in files if f in set(ctx.changed)]
    problems = []
    for rel in filter(None, files):
        path = os.path.join(REPO_ROOT, rel)
        try:
            with open(path, "rb") as fh:
                source = fh.read()
            tokens = list(tokenize.tokenize(io.BytesIO(source).readline))
        except (OSError, tokenize.TokenError, SyntaxError):
            continue  # compileall reports a file that doesn't parse
        stack = []
        for tok in tokens:
            if tok.type == tokenize.FSTRING_START:
                quote = tok.string.lstrip("rRbBfFuU")
                stack.append((quote, tok.start[0]))
            elif tok.type == tokenize.FSTRING_END:
                if stack:
                    stack.pop()
            elif stack and tok.type != tokenize.FSTRING_MIDDLE:
                quote, line = stack[-1]
                why = None
                if tok.type == tokenize.COMMENT:
                    why = "a comment"
                elif "\\" in tok.string:
                    why = "a backslash"
                elif len(quote) == 1 and quote in tok.string:
                    why = f"its own quote ({quote})"
                elif len(quote) == 1 and tok.type in (tokenize.NL, tokenize.NEWLINE):
                    why = "a line break"
                if why:
                    problems.append(f"{rel}:{tok.start[0]}: f-string holds {why} inside its braces")
    if problems:
        return Result(False, "\n".join(sorted(set(problems))))
    return Result(True)


def check_tabs(ctx: Ctx) -> Result:
    files = [f for f in git("ls-files", *TAB_CHECK_PATHSPECS).split("\n") if f]
    if not files:
        # Never pass an empty argv to the formatter: it would check nothing and
        # still exit 0, so a broken pathspec would look like a pass.
        return Result(False, "The tab check matched no files: TAB_CHECK_PATHSPECS is stale.")
    if ctx.changed is not None:
        files = [f for f in files if f in set(ctx.changed)]
        if not files:
            return Result(True, skipped="no Paradox .txt file changed")
    # Chunked: the full list is thousands of paths.
    out, ok = [], True
    for i in range(0, len(files), 400):
        res = sh(ctx, [PY, "scripts/format_paradox_tabs.py", "--check", *files[i:i + 400]])
        ok = ok and res.ok
        out.append(res.output)
    return Result(ok, "".join(out))


def check_organize_loc(ctx: Ctx) -> Result:
    res = sh(ctx, [PY, "organize_loc.py", "--check"])
    if not res.ok or not ctx.ci:
        return res
    # CI also runs the writer and checks the tree: git diff catches tracked
    # edits and deletions, status catches newly created files (#613, #617).
    writer = sh(ctx, [PY, "organize_loc.py"])
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", "localization/")
    if writer.ok and not dirty.strip():
        return Result(True)
    print(dirty)
    return Result(False, dirty)


def check_line_endings(ctx: Ctx) -> Result:
    problems = []
    for rel in CRLF_DOCS:
        try:
            with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
                data = fh.read()
        except OSError:
            problems.append(f"{rel}: missing (update CRLF_DOCS in scripts/preflight.py if it moved)")
            continue
        lines = data.count(b"\n")
        crlf = data.count(b"\r\n")
        if crlf != lines:
            problems.append(f"{rel}: {lines - crlf} of {lines} lines end in LF; this file is CRLF")
    return Result(not problems, "\n".join(problems))


def check_tests(ctx: Ctx) -> Result:
    tests = sorted(f for f in git("ls-files", "test_*.py").split("\n") if f)
    tests += sorted(
        f for f in git("ls-files", "--others", "--exclude-standard", "test_*.py").split("\n") if f
    )
    if ctx.changed is not None and not any(matches(p, MOD_CONTENT + DOCS) for p in ctx.changed):
        # Python-only diff: the changed tests, and the test named for each
        # changed module. Anything touching mod content or docs runs the lot,
        # because any test may read them.
        wanted = set()
        for path in ctx.changed:
            base = os.path.basename(path)
            if base.startswith("test_") and base in tests:
                wanted.add(base)
            elif base.endswith(".py") and f"test_{base}" in tests:
                wanted.add(f"test_{base}")
        if not wanted:
            return Result(True, skipped="no test is named for a changed file")
        tests = sorted(wanted)
    # --dist loadfile runs each file whole on one worker, as unittest does;
    # under loadscope a file's classes are split and tearDownModule runs early.
    argv = [PY, "-m", "pytest", "-n", "auto", "--dist", "loadfile", "-p", "no:cacheprovider", "-q"]
    if ctx.ci:
        argv.append("--durations=25")
    return sh(ctx, argv + tests)


def check_audits(ctx: Ctx) -> Result:
    argv = [PY, "scripts/run_audits.py"]
    return sh(ctx, argv)


CHECKS: tuple[Check, ...] = (
    # --- python ---------------------------------------------------------------
    Check("compile", "python", "Byte-compile every Python file",
          command(PY, "-m", "compileall", "-q", "."), PYTHON),
    Check("py311", "python", "No f-string syntax Python 3.11 rejects",
          check_py311_fstrings, PYTHON,
          fix="Lift the quoted or backslashed part out of the braces into a variable."),
    Check("ruff", "python", "Lint (ruff, pyflakes rules)",
          command(PY, "-m", "ruff", "check", "."), PYTHON + ("ruff.toml",)),
    # --- tests ----------------------------------------------------------------
    Check("tests", "tests", "Unit tests (pytest, one worker per CPU)",
          check_tests, slow=True,
          fix="Rerun one file with `.venv/bin/python -m pytest test_<name>.py -q`."),
    # --- content --------------------------------------------------------------
    Check("tabs", "content", "Paradox tab indentation",
          check_tabs, ("common/*", "events/*", "scripts/format_paradox_tabs.py"),
          fix="Run `python3 scripts/format_paradox_tabs.py <files>` on the files it names."),
    Check("loc-files", "content", "Localization file sanity (BOM, header, duplicate keys, quotes)",
          command(PY, "scripts/analysis/check_localization_files.py"),
          ("localization/*", "i18n/*", "scripts/analysis/check_localization_files.py")),
    Check("spelling", "content", "Localization and player guide spelling (American)",
          command(PY, "scripts/analysis/check_loc_spelling.py", "--check"),
          ("localization/*", "docs/player_guide/*", "scripts/analysis/check_loc_spelling.py"),
          fix="Run `python3 scripts/analysis/check_loc_spelling.py` (no --check) and commit what it rewrote."),
    Check("organize-loc", "content", "Localization keys sit where organize_loc files them",
          check_organize_loc, ("localization/*", "organize_loc.py"),
          fix="Run `python3 organize_loc.py` and commit everything it rewrote, new files and deletions included."),
    Check("line-endings", "content", "The CRLF docs are still CRLF",
          check_line_endings, CRLF_DOCS,
          fix="Restore the file's line endings (`unix2dos <file>`, or redo the edit with "
              "newline=\"\" on read and write)."),
    # --- audits ---------------------------------------------------------------
    Check("audits", "audits", "The offline audits (audit_registry.py), in parallel",
          check_audits, MOD_CONTENT + PYTHON + ("docs/engine/*", "vanilla_parsed/*"),
          fix="Each failing audit prints its own fix and suppression comment above."),
    # --- docs -----------------------------------------------------------------
    Check("audit-docs", "docs", "docs/guides/audits.md matches the audit registry",
          command(PY, "audit_registry.py", "--check"),
          ("audit_registry.py", "docs/guides/audits.md"),
          fix="Run `python3 audit_registry.py --write` and commit docs/guides/audits.md."),
    Check("rosters", "docs", "Post-load rosters are documented",
          command(PY, "scripts/analysis/check_post_load_rosters.py"),
          ("mod_state_server.py", "audit_registry.py", "docs/*", "CLAUDE.md",
           "scripts/analysis/check_post_load_rosters.py")),
    Check("guide-style", "docs", "Player guide style lint",
          command(PY, "scripts/analysis/check_player_guide_style.py", "--strict"),
          ("docs/player_guide/*", "localization/*", "scripts/analysis/check_player_guide_style.py")),
    Check("guide-pdf", "docs", "Player guide PDF matches its sources",
          command(PY, "scripts/build_player_guide.py", "--check"),
          ("docs/player_guide/*", "scripts/build_player_guide.py", "scripts/player_guide_figures.py"),
          fix="Run `.venv/bin/python scripts/build_player_guide.py` and commit the PDF with the chapters."),
)

GROUPS = tuple(dict.fromkeys(c.group for c in CHECKS))


def select(args, changed):
    chosen = []
    for check in CHECKS:
        if args.only and check.group not in args.only and check.id not in args.only:
            continue
        if check.group in args.skip or check.id in args.skip:
            continue
        if args.quick and check.slow:
            continue
        if changed is not None and check.triggers and not any(matches(p, check.triggers) for p in changed):
            continue
        chosen.append(check)
    return chosen


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    names = ", ".join(GROUPS)
    parser.add_argument("--only", nargs="+", default=[], metavar="NAME",
                        help=f"Run only these groups ({names}) or check ids.")
    parser.add_argument("--skip", nargs="+", default=[], metavar="NAME",
                        help="Leave out these groups or check ids.")
    parser.add_argument("--quick", action="store_true", help="Leave out the test suite.")
    parser.add_argument("--changed", action="store_true",
                        help="Run only what the diff against --base can affect.")
    parser.add_argument("--base", default="origin/main", help="Ref --changed compares with.")
    parser.add_argument("--ci", action="store_true",
                        help="CI mode: stream each check's output, and run organize_loc's writer.")
    parser.add_argument("--real-paths", action="store_true",
                        help="Use this machine's game paths instead of CI's dummy ones.")
    parser.add_argument("--list", action="store_true", help="List the checks and exit.")
    args = parser.parse_args(argv)

    known = set(GROUPS) | {c.id for c in CHECKS}
    unknown = [n for n in args.only + args.skip if n not in known]
    if unknown:
        parser.error(f"unknown group or check: {', '.join(unknown)} (known: {', '.join(sorted(known))})")

    if args.list:
        for check in CHECKS:
            print(f"{check.group:8} {check.id:13} {check.title}")
        return 0

    changed = changed_paths(args.base) if args.changed else None
    if changed is not None and not changed:
        print(f"Nothing differs from {args.base}; nothing to check.")
        return 0
    ctx = Ctx(env=run_audits.child_env(args.real_paths), ci=args.ci, changed=changed)
    checks = select(args, changed)
    if not checks:
        print("No check applies to this selection.")
        return 0

    failed = []
    started = time.monotonic()
    for check in checks:
        if args.ci:
            print(f"::group::{check.title}", flush=True)
        elif check.slow:
            print(f"....  {check.id:13} {check.title} (a few minutes)", flush=True)
        t0 = time.monotonic()
        result = check.run(ctx)
        seconds = time.monotonic() - t0
        if args.ci:
            print("::endgroup::", flush=True)
        if result.skipped:
            print(f"skip  {check.id:13} {result.skipped}", flush=True)
            continue
        if result.ok:
            print(f"ok    {check.id:13} {check.title}  ({seconds:.0f}s)", flush=True)
            continue
        failed.append(check)
        if args.ci:
            print(f"::error title={check.title}::{check.title} failed. {check.fix}", flush=True)
        print(f"FAIL  {check.id:13} {check.title}  ({seconds:.0f}s)")
        tail = result.output.rstrip().splitlines()[-80:]
        for line in tail:
            print("      " + line)
        if check.fix:
            print(f"      Fix: {check.fix}")
        print(f"      Rerun: {os.path.basename(PY)} scripts/preflight.py --only {check.id}", flush=True)

    total = time.monotonic() - started
    ran = len(checks)
    if failed:
        print(f"\n{len(failed)} of {ran} checks failed in {total:.0f}s: " + ", ".join(c.id for c in failed))
        return 1
    scope = " (scoped to the diff: run without --changed before you push)" if args.changed else ""
    left_out = " The test suite was left out." if args.quick else ""
    print(f"\nAll {ran} checks passed in {total:.0f}s{scope}.{left_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
