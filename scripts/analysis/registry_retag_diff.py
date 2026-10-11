#!/usr/bin/env python3
"""What a known-noise registry edit changes, measured on archived logs.

`docs/vanilla/vanilla_known_bugs.md` and `docs/audits/mod_known_noise.md`
decide which log lines triage hides. An edit that looks narrower can still
hide a mod error: a signature that is only a file path matches every error
whose stack runs through that file, an entry with a `- source:` anchor and an
empty code block matches every line from that cpp source (#873). Reading the
diff doesn't show that; tagging real logs with both versions does.

    corpus OUT.json.gz DIR...   Read every error*/debug* log under each DIR
                                (recursively) into one corpus. A line logged
                                in several files (rotations, minute copies)
                                counts once, at the largest count any single
                                file shows.
    diff CORPUS [--base REF]    Tag the corpus with the registries at git REF
                                (default origin/main) and in the working tree,
                                and list per entry the lines each gains or
                                loses, and how many of them have a mod frame.
                                Exit 1 when the working tree newly tags a line
                                whose stack holds a mod frame.
    modframed CORPUS            List, per entry of the working-tree registries,
                                the lines it tags whose stack holds a mod frame:
                                candidates for `- stack: vanilla only` (#863),
                                or mod errors an entry hides.

A mod frame is a path in the line's `files` that exists in the mod checkout
(`--mod-root`, default path_constants.mod_path; use the full checkout, since a
sparse worktree has no `gfx/`). Workflow: the log-triage skill, 2026-10-11.
"""
from __future__ import annotations

import argparse
import collections
import glob
import gzip
import json
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

import game_log_reader as glr  # noqa: E402

VANILLA_DOC = "docs/vanilla/vanilla_known_bugs.md"
MOD_NOISE_DOC = "docs/audits/mod_known_noise.md"
OPEN_ISSUES_DOC = "docs/audits/open_issues.md"


def build_corpus(roots: list[str]) -> list[dict]:
    """[{source, message, count, runs}] over every error*/debug* log under
    `roots`, one row per distinct (source, message)."""
    rows: dict[tuple[str, str], dict] = {}
    for root in roots:
        run = os.path.basename(os.path.normpath(root))
        for path in sorted(glob.glob(os.path.join(root, "**", "*.log"), recursive=True)):
            if not os.path.basename(path).startswith(("error", "debug")):
                continue
            try:
                entries = glr.parse_log(path)
            except (OSError, UnicodeDecodeError) as exc:
                print(f"skipped {path}: {exc}", file=sys.stderr)
                continue
            for (source, message), n in collections.Counter(
                    (e.source, e.message) for e in entries).items():
                row = rows.setdefault((source, message), {
                    "source": source, "message": message, "count": 0, "runs": []})
                row["count"] = max(row["count"], n)
                if run not in row["runs"]:
                    row["runs"].append(run)
    return list(rows.values())


def save_corpus(rows: list[dict], path: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(rows, fh)


def load_corpus(path: str) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def tag(rows: list[dict], docs_root: str, mod_root: str) -> list[dict | None]:
    """Each row's `vanilla_bug_ref` under the registries in `docs_root`
    (a directory holding docs/vanilla/... and docs/audits/...), as /logs
    tags them."""
    glr._vanilla_bug_cache.clear()
    _, vb, vs, _ = glr.load_vanilla_bug_registry(os.path.join(docs_root, VANILLA_DOC))
    _, mb, ms, _ = glr.load_mod_noise_registry(os.path.join(docs_root, MOD_NOISE_DOC))
    entries = [glr.LogEntry("00:00:00", r["source"], r["message"]) for r in rows]
    glr.tag_vanilla_bugs(entries, vb, vs, mod_root=mod_root)
    glr.tag_vanilla_bugs(entries, mb, ms, mod_root=mod_root)
    return [e.vanilla_bug_ref for e in entries]


def export_registries(ref: str, out_root: str) -> None:
    """Write the registries (and open_issues.md, which anchors resolve
    against) as of git `ref` under `out_root`."""
    for rel in (VANILLA_DOC, MOD_NOISE_DOC, OPEN_ISSUES_DOC):
        text = subprocess.run(["git", "-C", REPO_ROOT, "show", f"{ref}:{rel}"],
                              check=True, capture_output=True, text=True).stdout
        dest = os.path.join(out_root, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)


def _kernel(message: str) -> str:
    lines = [ln.strip() for ln in message.split("\n") if ln.strip()]
    return next((ln[7:] for ln in lines if ln.startswith("Error: ")), lines[0] if lines else "")


def diff(rows: list[dict], old: list, new: list, mod_root: str) -> dict:
    """{"tagged": {old, new}, "lost": {title: [row]}, "gained": {title: [row]}}
    where each row adds `mod_frame`, `old` and `new` titles."""
    has_mod_frame = glr.mod_frame_test(mod_root)
    out = {"tagged": {"old": 0, "new": 0}, "lost": collections.defaultdict(list),
           "gained": collections.defaultdict(list)}
    for row, o, n in zip(rows, old, new):
        to, tn = (o or {}).get("title"), (n or {}).get("title")
        out["tagged"]["old"] += row["count"] if to else 0
        out["tagged"]["new"] += row["count"] if tn else 0
        if to == tn:
            continue
        flip = {**row, "old": to, "new": tn,
                "mod_frame": has_mod_frame(glr.LogEntry("0", row["source"], row["message"]).files)}
        if to:
            out["lost"][to].append(flip)
        if tn:
            out["gained"][tn].append(flip)
    return out


def _print_group(label: str, groups: dict, other: str, shown: int) -> None:
    for title, flips in sorted(groups.items(), key=lambda kv: -sum(f["count"] for f in kv[1])):
        total = sum(f["count"] for f in flips)
        modded = sum(f["count"] for f in flips if f["mod_frame"])
        print(f"\n{label} {total} lines ({modded} with a mod frame): {title}")
        for f in sorted(flips, key=lambda f: -f["count"])[:shown]:
            print(f"  {f['count']:6d} {'MOD ' if f['mod_frame'] else '    '}"
                  f"{other} {f[other]!r}: {_kernel(f['message'])[:150]}")


def cmd_diff(args) -> int:
    rows = load_corpus(args.corpus)
    with tempfile.TemporaryDirectory() as base_root:
        export_registries(args.base, base_root)
        old = tag(rows, base_root, args.mod_root)
    new = tag(rows, REPO_ROOT, args.mod_root)
    result = diff(rows, old, new, args.mod_root)
    print(f"lines tagged: {args.base} {result['tagged']['old']}, working tree {result['tagged']['new']} "
          f"({len(rows)} distinct lines)")
    _print_group("LOST", result["lost"], "new", args.show)
    _print_group("GAINED", result["gained"], "old", args.show)
    hidden = sum(f["count"] for flips in result["gained"].values() for f in flips if f["mod_frame"])
    if hidden:
        print(f"\n{hidden} newly tagged lines have a mod frame in their stack.")
    return 1 if hidden else 0


def cmd_modframed(args) -> int:
    rows = load_corpus(args.corpus)
    refs = tag(rows, REPO_ROOT, args.mod_root)
    has_mod_frame = glr.mod_frame_test(args.mod_root)
    per: dict = collections.defaultdict(collections.Counter)
    for row, ref in zip(rows, refs):
        if ref is None:
            continue
        files = glr.LogEntry("0", row["source"], row["message"]).files
        mod_files = [f for f in files if has_mod_frame([f])]
        if mod_files:
            per[ref["title"]][(_kernel(row["message"])[:120], ", ".join(mod_files[:3]))] += row["count"]
    for title, lines in sorted(per.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"\n{sum(lines.values())} lines with a mod frame: {title}")
        for (kernel, mods), n in lines.most_common(args.show):
            print(f"  {n:6d} {kernel}\n         via {mods}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("corpus", help="build a corpus from log directories")
    c.add_argument("out")
    c.add_argument("roots", nargs="+")
    for name in ("diff", "modframed"):
        p = sub.add_parser(name)
        p.add_argument("corpus")
        p.add_argument("--mod-root", default=None)
        p.add_argument("--show", type=int, default=6, help="lines listed per entry")
        if name == "diff":
            p.add_argument("--base", default="origin/main")
    args = ap.parse_args(argv)
    if args.cmd == "corpus":
        rows = build_corpus(args.roots)
        save_corpus(rows, args.out)
        print(f"{len(rows)} distinct lines -> {args.out}")
        return 0
    if args.mod_root is None:
        from path_constants import mod_path
        args.mod_root = mod_path
    return cmd_diff(args) if args.cmd == "diff" else cmd_modframed(args)


if __name__ == "__main__":
    sys.exit(main())
