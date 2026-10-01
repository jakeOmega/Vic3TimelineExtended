"""What did a vanilla patch change, and does the mod use it? (no vanilla clone needed)

The runbook's default OLD_REF is a commit in the vanilla mirror (`~/src/vic3`),
which lags the install whenever nobody has committed the last hotfixes into it.
Two artefacts already hold the *previous* version without it:

* the committed `vanilla_parsed/` snapshot (git history: `HEAD` is the version
  the mod was last migrated on), and
* the previous `script_docs` dump (`~/src/vic3-engine-docs/<old>/docs`, or a
  Modding-Digests `docs/` folder).

Subcommands:

  parsed [--old-ref REF | --old-dir DIR] [--new-dir DIR] [--out DIR] [--mod-uses]
      Per entity type, which vanilla entities were removed / added / changed
      between the old and new `vanilla_parsed/` snapshots (run
      `python3 vanilla_parsed.py build` on the new install first). With --out,
      writes `<type>.diff`: a unified diff of each changed entity rendered back
      to Paradox-like text, so "what did vanilla edit in these 57 journal
      entries" is a file to read. Also diffs English loc keys.

  docs OLD_DOCS_DIR NEW_DOCS_DIR [--show-changed] [--mod-uses]
      Section-level diff of effects.log, triggers.log, event_targets.log,
      modifiers.log and on_actions.log. The ~3,300 regional iterators
      (`every_country_in_<region>` and kin) are skipped: their descriptions leak
      unrelated script and reshuffle on every dump.

`--mod-uses` greps the mod (common/ events/ gui/ localization/english/) for
every REMOVED name and prints the hits; comment-only hits are counted apart.
That join is what `/validate/vanilla-surface-diff` is meant to do, without
needing an old ref. Unit test: `test_vanilla_patch_diff.py`.
"""
import argparse
import collections
import difflib
import glob
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Section header per engine-doc log. effects/triggers use `## name`,
# event_targets uses `### name`, modifiers/on_actions use a `name:` line.
_DOC_HEADERS = {
    "effects.log": r"^## (\S+)\s*$",
    "triggers.log": r"^## (\S+)\s*$",
    "event_targets.log": r"^### (\S+)\s*$",
    "modifiers.log": r"^([A-Za-z0-9_]+):\s*$",
    "on_actions.log": r"^([A-Za-z0-9_]+):\s*$",
}

_REGION_ITERATOR = re.compile(r"^(every|any|random|ordered)_\w+_in_(\w+)$")
# A suffix shared by this many iterator headers is a map region, not a scope.
_REGION_SUFFIX_MIN = 8

MOD_ROOTS = ("common", "events", "gui", "localization/english")

_OPERATORS = ("=", ">", "<", ">=", "<=", "!=", "?=", "==")


# ---------------------------------------------------------------- engine docs

def load_sections(path, header):
    """{section name: normalised body} for one engine-doc log ({} if missing)."""
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read().replace("\r", "")
    sections = collections.OrderedDict()
    current = None
    for line in text.split("\n"):
        m = re.match(header, line)
        if m:
            current = m.group(1)
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line.rstrip())
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def region_suffixes(names):
    """Map-region names, read off iterator headers: `every_country_in_<region>` and
    its seven siblings put eight headers on one suffix in effects.log."""
    counts = collections.Counter(m.group(2) for n in names if (m := _REGION_ITERATOR.match(n)))
    return {suffix for suffix, n in counts.items() if n >= _REGION_SUFFIX_MIN}


def _is_region_iterator(name, suffixes):
    m = _REGION_ITERATOR.match(name)
    return bool(m and m.group(2) in suffixes)


def diff_doc_file(old_path, new_path, header, suffixes=None):
    """(removed, added, changed) name lists for one log; changed carries a diff.

    `suffixes` are the map-region names whose iterators to skip; by default they
    are read off this log's own headers, which only works for effects.log (the
    other logs carry one iterator kind per region), so `diff_docs` passes them in.
    """
    old = load_sections(old_path, header)
    new = load_sections(new_path, header)
    if suffixes is None:
        suffixes = region_suffixes(set(old) | set(new))
    skip = {n for n in set(old) | set(new) if _is_region_iterator(n, suffixes)}
    removed = sorted(k for k in set(old) - set(new) if k not in skip)
    added = sorted(k for k in set(new) - set(old) if k not in skip)
    changed = {}
    for k in old:
        if k in new and k not in skip and old[k] != new[k]:
            changed[k] = [l for l in difflib.unified_diff(
                old[k].split("\n"), new[k].split("\n"), lineterm="", n=0)
                if not l.startswith(("---", "+++", "@@"))]
    return removed, added, changed


def diff_docs(old_dir, new_dir):
    """{log file: (removed, added, changed)} for the five logs."""
    effects = _DOC_HEADERS["effects.log"]
    names = set()
    for d in (old_dir, new_dir):
        names |= set(load_sections(os.path.join(d, "effects.log"), effects))
    suffixes = region_suffixes(names)
    return {name: diff_doc_file(os.path.join(old_dir, name),
                                os.path.join(new_dir, name), header, suffixes)
            for name, header in _DOC_HEADERS.items()}


# ------------------------------------------------------------- parsed vanilla

def _is_pair(x):
    return isinstance(x, list) and len(x) == 2 and isinstance(x[0], str) and x[0] in _OPERATORS


def render_entry(key, val, indent=0):
    """Render one parsed `key -> [op, value]` (or a list of them) as Paradox-like lines."""
    tab = "\t" * indent
    if not isinstance(val, list):  # a localization value, not a parsed block
        return [f"{tab}{key} = {val}"]
    lines = []
    for pair in ([val] if _is_pair(val) else val):
        if not _is_pair(pair):
            lines.append(f"{tab}{key} <?> {json.dumps(pair)[:200]}")
            continue
        op, x = pair
        if isinstance(x, dict):
            lines.append(f"{tab}{key} {op} {{")
            for k, v in x.items():
                lines += render_entry(k, v, indent + 1)
            lines.append(tab + "}")
        elif isinstance(x, list):
            lines.append(f"{tab}{key} {op} [list] {json.dumps(x)[:300]}")
        else:
            lines.append(f"{tab}{key} {op} {x}")
    return lines


def diff_entities(old, new):
    """(removed, added, changed names, {name: unified diff lines}) between two parses."""
    removed = [k for k in old if k not in new]
    added = [k for k in new if k not in old]
    changed = [k for k in old if k in new and old[k] != new[k]]
    diffs = {}
    for k in changed:
        diffs[k] = [l for l in difflib.unified_diff(
            render_entry(k, old[k]), render_entry(k, new[k]), lineterm="", n=2)
            if not l.startswith(("---", "+++"))]
    return removed, added, changed, diffs


def _git_show_json(ref, rel_path):
    r = subprocess.run(["git", "show", f"{ref}:{rel_path}"], capture_output=True,
                       text=True, cwd=REPO_ROOT)
    return json.loads(r.stdout) if r.returncode == 0 else None


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def diff_parsed(new_dir, old_ref=None, old_dir=None):
    """{snapshot file name: (removed, added, changed, diffs)} for changed snapshot files.

    `new_dir` is a `vanilla_parsed/`-shaped directory; the old side is either
    another such directory (`old_dir`) or the same tree at a git ref.
    """
    out = {}
    files = sorted(glob.glob(os.path.join(new_dir, "common", "*.json"))
                   + [os.path.join(new_dir, "localization_english.json")])
    for path in files:
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, new_dir)
        if old_dir:
            old_path = os.path.join(old_dir, rel)
            old = _load_json(old_path) if os.path.isfile(old_path) else None
        else:
            old = _git_show_json(old_ref or "HEAD", "vanilla_parsed/" + rel.replace(os.sep, "/"))
        if old is None:
            out[rel] = (["<whole type absent in the old snapshot>"], [], [], {})
            continue
        new = _load_json(path)
        res = diff_entities(old, new)
        if res[0] or res[1] or res[2]:
            out[rel] = res
    return out


# -------------------------------------------------------------------- mod uses

def mod_uses(names, repo=REPO_ROOT):
    """{name: {'code': [file:line, ...], 'comment': n}} for names the mod mentions."""
    hits = {}
    for name in sorted(set(names)):
        r = subprocess.run(["git", "grep", "-n", "-w", "-F", name, "--", *MOD_ROOTS],
                           capture_output=True, text=True, cwd=repo)
        code, comment = [], 0
        for line in r.stdout.splitlines():
            path, lineno, text = line.split(":", 2)
            if text.lstrip().startswith("#"):
                comment += 1
            else:
                code.append(f"{path}:{lineno}")
        if code or comment:
            hits[name] = {"code": code, "comment": comment}
    return hits


def print_mod_uses(names):
    hits = mod_uses(names)
    print(f"\n== removed names the mod mentions: {len(hits)} of {len(set(names))}")
    for name, h in hits.items():
        more = f" (+{len(h['code']) - 3} more)" if len(h["code"]) > 3 else ""
        print(f"  {name}: {len(h['code'])} code hit(s), {h['comment']} comment-only"
              f"{'  ' + ', '.join(h['code'][:3]) + more if h['code'] else ''}")


# ------------------------------------------------------------------------- CLI

def _cmd_docs(args):
    results = diff_docs(args.old, args.new)
    removed_names = []
    for name, (removed, added, changed) in results.items():
        print(f"##### {name}: removed {len(removed)}, added {len(added)}, changed {len(changed)}")
        if removed:
            print("  REMOVED:", ", ".join(removed))
        if added:
            print("  ADDED:  ", ", ".join(added))
        for k, lines in changed.items():
            print(f"  CHANGED: {k}")
            if args.show_changed:
                for line in lines[:20]:
                    print("      " + line[:200])
        removed_names += removed
    if args.mod_uses:
        print_mod_uses(removed_names)
    return 0


def _cmd_parsed(args):
    new_dir = os.path.join(REPO_ROOT, args.new_dir)
    results = diff_parsed(new_dir, old_ref=args.old_ref, old_dir=args.old_dir)
    removed_names = []
    if args.out:
        os.makedirs(args.out, exist_ok=True)
    for rel, (removed, added, changed, diffs) in sorted(results.items()):
        print(f"{rel:42s} removed={len(removed):4d} added={len(added):4d} changed={len(changed):4d}")
        removed_names += [r for r in removed if not r.startswith("<")]
        if not args.out:
            continue
        stem = os.path.splitext(os.path.basename(rel))[0]
        with open(os.path.join(args.out, stem + ".diff"), "w", encoding="utf-8") as fh:
            fh.write(f"REMOVED: {removed}\nADDED: {added}\nCHANGED: {changed}\n\n")
            for k in changed:
                fh.write(f"@@@@@@ {k}\n" + "\n".join(diffs[k]) + "\n")
    if args.mod_uses:
        print_mod_uses(removed_names)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parsed", help="diff two vanilla_parsed/ snapshots")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--old-ref", default="HEAD", help="git ref holding the old vanilla_parsed/ (default HEAD)")
    src.add_argument("--old-dir", help="a directory shaped like vanilla_parsed/ instead of a git ref")
    p.add_argument("--new-dir", default="vanilla_parsed", help="new snapshot, relative to the repo root")
    p.add_argument("--out", help="write a <type>.diff per changed type into this directory")
    p.add_argument("--mod-uses", action="store_true", help="grep the mod for removed entity names")
    p.set_defaults(func=_cmd_parsed)
    d = sub.add_parser("docs", help="diff two script_docs dumps")
    d.add_argument("old", help="old docs dir (holds effects.log, triggers.log, ...)")
    d.add_argument("new", help="new docs dir")
    d.add_argument("--show-changed", action="store_true", help="print the changed lines of each changed section")
    d.add_argument("--mod-uses", action="store_true", help="grep the mod for removed names")
    d.set_defaults(func=_cmd_docs)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
