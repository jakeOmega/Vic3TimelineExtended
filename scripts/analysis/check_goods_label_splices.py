"""Goods names in goods-keyed modifier labels must be `$good$` splices.

A modifier label that spells a good out ("@iron! Iron input") keeps showing that
text after the good is renamed: the mod calls `iron` Structural Metals, yet for a
long time its modifier tooltips said "Iron input". Vanilla already splices in
some labels (`goods_iron_output_mult:0 "$iron$ Goods Output"`,
`goods_output_merchant_marine_add`), and the mod follows it everywhere, so a
good's name lives in exactly one key and every label follows a rename.

Checks:
  1. Every goods-keyed modifier label the mod defines (any `*_add` / `*_mult`
     key, and its `_desc`, whose name contains a good's key) splices the good
     instead of spelling out its name. `te_unused_l_english.yml` is skipped.
  2. For every good the mod renames (its name key differs from vanilla's),
     each vanilla label that spells the good out is overridden in the
     `replace/` file with the spliced text.

Labels of building groups (`building_group_bg_mining_*`) and buildings
(`building_coal_mine_*`) name the group or building, not the good, and are
left alone. So is a label for a good the mod does not rename, whose vanilla
text is already right.

Usage:
    python3 scripts/analysis/check_goods_label_splices.py [--fix]

Exits 1 and prints one line per label when any spells a name out; `--fix`
rewrites the mod's labels in place and appends the vanilla overrides to the
`replace/` file. Exits 0 when clean.
"""

from __future__ import annotations

import glob
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OVERRIDE_FILE = os.path.join("localization", "english", "replace", "timeline_extended_override_l_english.yml")
SKIP_FILES = {"te_unused_l_english.yml"}

LOC_LINE = re.compile(r'^(\s+)([^\s:#]+)(:\d*)?(\s*)"(.*)"(\s*)$')
TOP_KEY = re.compile(r"^(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:|TRY_INJECT:|TRY_REPLACE:)?([A-Za-z0-9_]+)\s*=\s*\{")
MODIFIER_LIKE = re.compile(r"(_add|_mult)(_desc)?$")


def _top_keys(directory: str) -> set[str]:
    keys: set[str] = set()
    for path in glob.glob(os.path.join(directory, "*.txt")):
        with open(path, encoding="utf-8-sig", errors="ignore") as fh:
            for line in fh:
                m = TOP_KEY.match(line)
                if m:
                    keys.add(m.group(1))
    return keys


def _mod_loc_files(repo_root: str) -> list[str]:
    loc_dir = os.path.join(repo_root, "localization", "english")
    top = sorted(p for p in glob.glob(os.path.join(loc_dir, "*.yml")) if os.path.basename(p) not in SKIP_FILES)
    return top + sorted(glob.glob(os.path.join(loc_dir, "replace", "*.yml")))


def _read_loc(paths: list[str]) -> dict[str, tuple[str, str]]:
    """{key: (value, path)}; a later file wins, as `replace/` does in game."""
    out: dict[str, tuple[str, str]] = {}
    for path in paths:
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                m = LOC_LINE.match(line.rstrip("\n"))
                if m:
                    out[m.group(2)] = (m.group(5), path)
    return out


def _good_of(key: str, goods: list[str], buildings_by_good: dict[str, list[str]]) -> str | None:
    if key.startswith("building_group_") or not MODIFIER_LIKE.search(key):
        return None
    base = re.sub(r"_desc$", "", key)
    for good in goods:  # longest first, so luxury_clothes wins over clothes
        if re.search(rf"(^|_){re.escape(good)}(_|$)", base):
            if any(b in base for b in buildings_by_good.get(good, ())):
                return None
            return good
    return None


def _name_forms(good: str, vanilla_loc: dict[str, str], mod_loc: dict[str, tuple[str, str]]) -> list[str]:
    names = set()
    if good in vanilla_loc:
        names.add(vanilla_loc[good])
    if good in mod_loc:
        names.add(mod_loc[good][0])
    names = {n for n in names if n and "$" not in n and "[" not in n}
    # Vanilla labels sometimes use the singular ("@radios! Radio input").
    names |= {n[:-1] for n in names if n.endswith("s") and not n.endswith("ss")}
    return sorted(names, key=len, reverse=True)


def _splice(value: str, good: str, forms: list[str]) -> str:
    for name in forms:
        value = re.sub(rf"(?<![\w$]){re.escape(name)}(?![\w$])", f"${good}$", value)
    return value


def find(repo_root: str = REPO_ROOT, snapshot=None):
    """Return (mod_fixes, vanilla_overrides).

    mod_fixes: [(path, key, old, new)] for mod-defined labels.
    vanilla_overrides: [(key, old, new)] for vanilla labels of renamed goods.
    `snapshot` is a `vanilla_parsed.Snapshot` (or anything with `.data` and
    `.localization`); by default the committed snapshot is loaded.
    """
    if snapshot is None:
        sys.path.insert(0, repo_root)
        import vanilla_parsed

        snapshot = vanilla_parsed.load(os.path.join(repo_root, "vanilla_parsed"))
    vanilla_loc: dict[str, str] = snapshot.localization
    goods = set(snapshot.data.get("Goods", {})) | _top_keys(os.path.join(repo_root, "common", "goods"))
    goods_sorted = sorted(goods, key=len, reverse=True)
    buildings = set(snapshot.data.get("Buildings", {})) | _top_keys(os.path.join(repo_root, "common", "buildings"))
    buildings_by_good: dict[str, list[str]] = {}
    for good in goods:
        token = re.compile(rf"(^|_){re.escape(good)}(_|$)")
        buildings_by_good[good] = [b for b in buildings if token.search(b)]

    mod_loc = _read_loc(_mod_loc_files(repo_root))
    renamed = {g for g in goods if g in mod_loc and g in vanilla_loc and mod_loc[g][0] != vanilla_loc[g]}

    mod_fixes = []
    for key, (value, path) in sorted(mod_loc.items()):
        good = _good_of(key, goods_sorted, buildings_by_good)
        if good:
            new = _splice(value, good, _name_forms(good, vanilla_loc, mod_loc))
            if new != value:
                mod_fixes.append((path, key, value, new))

    vanilla_overrides = []
    for key, value in sorted(vanilla_loc.items()):
        if key in mod_loc:
            continue
        good = _good_of(key, goods_sorted, buildings_by_good)
        if good in renamed:
            new = _splice(value, good, _name_forms(good, vanilla_loc, mod_loc))
            if new != value:
                vanilla_overrides.append((key, value, new))
    return mod_fixes, vanilla_overrides


def fix(repo_root: str, mod_fixes, vanilla_overrides) -> None:
    by_path: dict[str, dict[str, str]] = {}
    for path, key, _old, new in mod_fixes:
        by_path.setdefault(path, {})[key] = new
    for path, todo in by_path.items():
        with open(path, encoding="utf-8-sig", newline="") as fh:
            lines = fh.read().split("\n")
        for i, line in enumerate(lines):
            m = LOC_LINE.match(line)
            if m and m.group(2) in todo:
                lines[i] = f'{m.group(1)}{m.group(2)}{m.group(3) or ""}{m.group(4)}"{todo[m.group(2)]}"{m.group(6)}'
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("\n".join(lines))
    if vanilla_overrides:
        path = os.path.join(repo_root, OVERRIDE_FILE)
        with open(path, encoding="utf-8-sig", newline="") as fh:
            text = fh.read()
        if not text.endswith("\n"):
            text += "\n"
        text += "".join(f' {key}:0 "{new}"\n' for key, _old, new in vanilla_overrides)
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(text)


def main(argv: list[str]) -> int:
    mod_fixes, vanilla_overrides = find()
    if "--fix" in argv:
        fix(REPO_ROOT, mod_fixes, vanilla_overrides)
        print(f"fixed {len(mod_fixes)} mod label(s), added {len(vanilla_overrides)} vanilla override(s)")
        return 0
    for path, key, old, new in mod_fixes:
        print(f"{os.path.relpath(path, REPO_ROOT)}: {key}: {old!r} should splice: {new!r}")
    for key, old, new in vanilla_overrides:
        print(f"{OVERRIDE_FILE}: missing override {key}: vanilla {old!r} should be {new!r}")
    if mod_fixes or vanilla_overrides:
        print(f"{len(mod_fixes) + len(vanilla_overrides)} goods label(s) spell a good's name out; "
              f"run with --fix to splice them")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
