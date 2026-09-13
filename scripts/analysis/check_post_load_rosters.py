"""Verify the post-load generator/audit rosters are fully documented (issue #248).

`mod_state_server.py` owns two canonical rosters — `POST_LOAD_REGENERATORS`
(file-rewriting generators) and `POST_LOAD_AUDITS` (read-only audits). Three
docs restate them by hand:

* `CLAUDE.md`               — the "auto-run on /reload" bullet
* `docs/guides/python_tools.md` — the § "Auto-run on server reload" table
* `docs/auto_generated_files.md` — the generator -> output ownership map

Hand-maintained copies drift the moment someone appends a roster entry, which
is exactly what issue #248 found (11 modules missing across the three docs).
This checker closes the loop: it reads the rosters straight out of
`mod_state_server.py` and fails if any module name is missing from any of the
three docs.

The rosters are extracted with `ast`, not by importing `mod_state_server` —
importing pulls in the whole server (and, transitively, a resolved Victoria 3
install), which this check has no business requiring. `ast` sees the literal
list assignments, which is all we need.

Run:
    python3 scripts/analysis/check_post_load_rosters.py           # exit 1 on drift
    python3 scripts/analysis/check_post_load_rosters.py --list    # print rosters

Exit code 0 = every roster module is named in all three docs; 1 = drift (the
missing (module, doc) pairs are printed). Unit test: `test_post_load_rosters.py`.
"""
import argparse
import ast
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SERVER_FILE = "mod_state_server.py"

# Roster assignment name -> human label used in output.
ROSTERS = {
    "POST_LOAD_REGENERATORS": "regenerator",
    "POST_LOAD_AUDITS": "audit",
}

# Docs that restate the rosters and must name every module.
DOC_FILES = (
    "CLAUDE.md",
    os.path.join("docs", "guides", "python_tools.md"),
    os.path.join("docs", "auto_generated_files.md"),
)


def extract_rosters(server_path):
    """Return {roster_name: [module_label, ...]} parsed out of mod_state_server.py.

    Each roster is a module-level list of `(label, import_path)` tuples; we
    key on the label, which is what the docs spell.
    """
    with open(server_path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=server_path)

    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id not in ROSTERS:
                continue
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                raise SystemExit(
                    f"{target.id} in {SERVER_FILE} is no longer a literal list/tuple; "
                    "update scripts/analysis/check_post_load_rosters.py."
                )
            labels = []
            for elt in node.value.elts:
                if not isinstance(elt, (ast.Tuple, ast.List)) or not elt.elts:
                    raise SystemExit(
                        f"Unexpected entry in {target.id}: expected a "
                        "(label, module_path) tuple."
                    )
                first = elt.elts[0]
                if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
                    raise SystemExit(
                        f"Unexpected entry in {target.id}: first tuple element "
                        "is not a string literal."
                    )
                labels.append(first.value)
            found[target.id] = labels

    missing_rosters = sorted(set(ROSTERS) - set(found))
    if missing_rosters:
        raise SystemExit(
            f"Could not find {', '.join(missing_rosters)} in {SERVER_FILE}."
        )
    return found


def check_docs(rosters, repo_root=REPO_ROOT, doc_files=DOC_FILES):
    """Return a sorted list of (module, doc_rel_path) pairs the docs don't mention.

    A module counts as documented when its bare name appears as a whole word
    anywhere in the doc — the three docs spell it differently (`pm_costs`,
    `pm_costs.py`, `scripts/generators/gen_company_building_cleanup.py`), and a
    word-boundary match accepts all of those without hard-coding a format.
    """
    texts = {}
    for rel in doc_files:
        path = os.path.join(repo_root, rel)
        with open(path, encoding="utf-8") as fh:
            texts[rel] = fh.read()

    missing = []
    for modules in rosters.values():
        for module in modules:
            pattern = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(module) + r"(?![A-Za-z0-9_])")
            for rel, text in texts.items():
                if not pattern.search(text):
                    missing.append((module, rel))
    return sorted(missing)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--list", action="store_true",
        help="Print the rosters as read from mod_state_server.py and exit 0.",
    )
    args = parser.parse_args(argv)

    rosters = extract_rosters(os.path.join(REPO_ROOT, SERVER_FILE))

    if args.list:
        for name, label in ROSTERS.items():
            print(f"{name} ({len(rosters[name])} {label}s):")
            for module in rosters[name]:
                print(f"  {module}")
        return 0

    missing = check_docs(rosters)
    total = sum(len(v) for v in rosters.values())
    if missing:
        print(
            f"Post-load roster drift: {len(missing)} missing mention(s) "
            f"across {len(DOC_FILES)} docs ({total} modules checked)."
        )
        for module, rel in missing:
            print(f"  {rel}: does not mention `{module}`")
        print(
            "\nAdd a row/mention for each module, then re-run. The rosters live in "
            f"{SERVER_FILE} (POST_LOAD_REGENERATORS / POST_LOAD_AUDITS)."
        )
        return 1

    print(
        f"OK: all {total} post-load modules "
        f"({len(rosters['POST_LOAD_REGENERATORS'])} regenerators, "
        f"{len(rosters['POST_LOAD_AUDITS'])} audits) are named in "
        + ", ".join(DOC_FILES)
        + "."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
