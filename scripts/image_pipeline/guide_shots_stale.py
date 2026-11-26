#!/usr/bin/env python3
"""Which player guide pictures may be stale: the files a picture shows changed since it was taken (#2056).

    python3 scripts/image_pipeline/guide_shots_stale.py              # a report; exit 0
    python3 scripts/image_pipeline/guide_shots_stale.py --strict     # exit 1 when any picture is stale
    python3 scripts/image_pipeline/guide_shots_stale.py --json

Each shot of the manifest (`guide_shots.py`) names the files whose change can make its picture wrong (`depends_on`,
git pathspecs). A picture was taken at the commit `guide_shots_taken.json` records for it when `game_qa capture
--write` took it, else at the last commit that changed the picture's file (a picture added by hand). It is stale when
a commit since then changed one of its files. The working tree's uncommitted edits count too, so a PR that changes a
pictured panel sees the note before it is committed.

Stale is a prompt to look, not a verdict: a change to a tooltip's loc key in a file the picture depends on makes it
stale though nothing in the picture moved. The release checklist refreshes stale pictures on a major release, or on
one known to change what a picture shows (owner, 2026-11-25); preflight prints the list as a note and never fails on
it, since CI can't take pictures.

A checkout without the history the baseline needs (CI's shallow clone) prints that, and exits 0.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TAKEN_FILE = os.path.join(HERE, "guide_shots_taken.json")
sys.path.insert(0, HERE)

import guide_shots  # noqa: E402


def git(*args: str) -> tuple[int, str]:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
    return done.returncode, done.stdout


def taken() -> dict:
    if not os.path.isfile(TAKEN_FILE):
        return {}
    with open(TAKEN_FILE, encoding="utf-8") as f:
        return json.load(f)


def baseline(sid: str, shot: dict, records: dict) -> tuple[str | None, str]:
    """(commit, where it came from): the capture's record, else the last commit of the picture's file."""
    record = records.get(sid) or {}
    if record.get("commit"):
        code, _ = git("cat-file", "-e", record["commit"] + "^{commit}")
        if code == 0:
            return record["commit"], "capture"
        return None, "the recorded commit %s is not in this checkout" % record["commit"][:12]
    code, out = git("log", "-1", "--format=%H", "--", shot["out"])
    if code != 0 or not out.strip():
        return None, "no commit of %s in this checkout's history" % shot["out"]
    return out.strip(), "file"


def changed_since(commit: str, globs: list[str]) -> list[str]:
    """The files matching `globs` that changed after `commit`: committed since, or edited in the working tree."""
    specs = [":(glob)" + g if "*" in g else g for g in globs]
    files: set[str] = set()
    for args in (("diff", "--name-only", commit, "HEAD", "--"), ("diff", "--name-only", "HEAD", "--")):
        code, out = git(*args, *specs)
        if code == 0:
            files |= {line for line in out.splitlines() if line}
    return sorted(files)


def report() -> dict:
    records = taken()
    stale, fresh, unknown = {}, [], {}
    _code, shallow = git("rev-parse", "--is-shallow-repository")
    if shallow.strip() == "true":       # every file's last commit would be the clone's one: nothing to judge by
        return {"stale": stale, "fresh": fresh, "unknown": unknown, "shallow": True}
    for sid, shot in guide_shots.SHOTS.items():
        if shot["status"] == "placeholder" or not os.path.isfile(os.path.join(REPO, shot["out"])):
            continue
        commit, source = baseline(sid, shot, records)
        if commit is None:
            unknown[sid] = source
            continue
        files = changed_since(commit, shot.get("depends_on") or [])
        if files:
            _, subject = git("log", "-1", "--format=%cs", commit)
            stale[sid] = {"since": commit[:12], "taken": subject.strip(), "baseline": source, "files": files,
                          "status": shot["status"]}
        else:
            fresh.append(sid)
    return {"stale": stale, "fresh": fresh, "unknown": unknown, "shallow": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true", help="exit 1 when a picture is stale")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    found = report()
    if args.json:
        print(json.dumps(found, indent=1))
    else:
        if found["shallow"]:
            print("A shallow checkout: the pictures' history is not here, so staleness was not judged.")
            return 0
        for sid, info in found["stale"].items():
            more = "" if len(info["files"]) <= 4 else " and %d more" % (len(info["files"]) - 4)
            how = "taken by capture" if info["baseline"] == "capture" else "last changed"
            print("stale  %-32s %s %s (%s); since then: %s%s" % (
                sid, how, info["taken"], info["since"], ", ".join(info["files"][:4]), more))
        for sid, why in found["unknown"].items():
            print("?      %-32s %s" % (sid, why))
        print("%d of %d pictures may be stale. Refresh them with `python3 -m game_qa capture` (status pilot or "
              "entry) or by hand, on a major release or one that changes what they show."
              % (len(found["stale"]), len(found["stale"]) + len(found["fresh"]) + len(found["unknown"])))
    return 1 if args.strict and found["stale"] else 0


if __name__ == "__main__":
    sys.exit(main())
