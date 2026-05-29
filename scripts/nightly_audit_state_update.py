#!/usr/bin/env python3
"""Atomically update docs/audits/.nightly_coverage.json after a nightly audit.

Why this exists: nightly-audit agents previously hand-edited the JSON via Edit
or stream-appended new entries. Because `json.load` silently keeps only the
*last* of any duplicate key, an append-shaped edit would create a second copy
of an existing path and overwrite the older record's audit history on the next
load. Issue #166 documents 8 such duplicates surfacing on 2026-05-29.

Always update the state file by invoking this script — never by editing the
JSON directly.

Usage:
    python3 scripts/nightly_audit_state_update.py \\
        --targets-json docs/audits/nightly/2026-05-29/targets.json \\
        --findings-json -    # JSON on stdin, e.g. {"path/to/file.txt": 2}

    # Or read findings from a file:
    python3 scripts/nightly_audit_state_update.py \\
        --targets-json docs/audits/nightly/2026-05-29/targets.json \\
        --findings-json /tmp/findings.json

    # Dry-run prints the diff and exits 0 without writing.
    python3 scripts/nightly_audit_state_update.py ... --dry-run

The targets manifest supplies the file list, slice bounds, and run date; the
findings JSON supplies a `{repo_relative_path: finding_count}` map for that
run (omit a path → 0 findings).

Decay: any file *not* in the run whose `last_audited` is older than DECAY_DAYS
has its `recent_findings` halved (floor to 0). Mirrors the scoring decay used
by nightly_audit_select.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date as Date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_FILE = REPO_ROOT / "docs/audits/.nightly_coverage.json"
DECAY_DAYS = 90


def _parse_date(s: str) -> Date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_findings(arg: str) -> dict[str, int]:
    if arg == "-":
        raw = sys.stdin.read()
    else:
        with open(arg, encoding="utf-8") as f:
            raw = f.read()
    if not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise SystemExit("findings JSON must be an object mapping path -> int")
    out: dict[str, int] = {}
    for k, v in data.items():
        if not isinstance(v, int) or v < 0:
            raise SystemExit(f"findings count for {k!r} must be a non-negative int, got {v!r}")
        out[str(k)] = v
    return out


def update_state(
    state: dict,
    targets_doc: dict,
    findings: dict[str, int],
    run_date: Date,
) -> tuple[dict, list[str]]:
    """Return (new_state, list_of_change_lines). Pure — caller writes."""
    files: dict[str, dict] = state.setdefault("files", {})
    changes: list[str] = []
    touched: set[str] = set()

    for target in targets_doc.get("targets", []):
        path = target["path"]
        line_range = target.get("line_range")
        finding_count = findings.get(path, 0)
        touched.add(path)

        entry = files.setdefault(path, {})
        prev_count = entry.get("audit_count", 0)
        entry["audit_count"] = prev_count + 1
        entry["last_audited"] = run_date.isoformat()
        entry["recent_findings"] = finding_count
        if line_range is not None:
            partial = entry.setdefault("partial_coverage", [])
            slice_pair = [int(line_range[0]), int(line_range[1])]
            if slice_pair not in partial:
                partial.append(slice_pair)
        changes.append(
            f"  audited: {path} "
            f"(audit_count {prev_count} -> {entry['audit_count']}, "
            f"findings={finding_count}"
            + (f", slice={line_range}" if line_range else "")
            + ")"
        )

    decay_cutoff = run_date - timedelta(days=DECAY_DAYS)
    decayed = 0
    for path, entry in files.items():
        if path in touched:
            continue
        last = entry.get("last_audited")
        if not last:
            continue
        try:
            last_date = _parse_date(last)
        except ValueError:
            continue
        if last_date >= decay_cutoff:
            continue
        old = entry.get("recent_findings", 0)
        if old <= 0:
            continue
        new = old // 2
        if new != old:
            entry["recent_findings"] = new
            decayed += 1
    if decayed:
        changes.append(f"  decayed recent_findings on {decayed} stale entries")

    return state, changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--targets-json", required=True, help="Path to the run's targets.json")
    parser.add_argument(
        "--findings-json",
        required=True,
        help="Path to a JSON file mapping {repo-relative path: finding count}, or '-' for stdin.",
    )
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE), help="State file to update.")
    parser.add_argument("--date", help="Override the run date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the proposed changes; don't write the state file.",
    )
    args = parser.parse_args(argv)

    targets_path = Path(args.targets_json)
    state_path = Path(args.state_file)
    if not targets_path.is_file():
        print(f"error: targets file not found: {targets_path}", file=sys.stderr)
        return 2
    if not state_path.is_file():
        print(f"error: state file not found: {state_path}", file=sys.stderr)
        return 2

    targets_doc = _load_json(targets_path)
    findings = _load_findings(args.findings_json)
    state = _load_json(state_path)
    run_date = _parse_date(args.date) if args.date else Date.today()

    new_state, changes = update_state(state, targets_doc, findings, run_date)

    if not changes:
        print("no changes")
        return 0

    print(f"updating {state_path.relative_to(REPO_ROOT) if state_path.is_relative_to(REPO_ROOT) else state_path}:")
    for line in changes:
        print(line)

    if args.dry_run:
        print("(dry-run: not written)")
        return 0

    # Write back; sort_keys keeps the diff stable across runs.
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(new_state, f, indent=2, sort_keys=True)
        f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
