"""The run folder's record: one JSON line per step, and a summary a session reads first.

    <backup root>/runs/<snapshot id>/steps.jsonl   one object per step: its UTC time, the verb, what it found
    <backup root>/runs/<snapshot id>/summary.md    the restore's outcome first, then the run, then a table of the steps,
                                                   then one table per try-event check, a row per option

Nothing here touches the owner's files: the folder is the harness's own, under the backup root.
"""
from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Mapping
from pathlib import Path

STEPS_FILE = "steps.jsonl"
SUMMARY_FILE = "summary.md"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def stamp(when: dt.datetime) -> str:
    """`2026-11-10T15:00:00Z`: the form part 1's journals use."""
    return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Report:
    def __init__(self, run_dir: Path, now: Callable[[], dt.datetime] = utc_now) -> None:
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.steps_path = self.dir / STEPS_FILE
        self.summary_path = self.dir / SUMMARY_FILE
        self._now = now

    def step(self, verb: str, **fields) -> None:
        """Append one line: `time` (UTC; a `time` among `fields` is kept instead, for a step recorded before the
        folder existed), `verb`, then `fields`. A value JSON cannot hold is written as its text."""
        record = {"time": stamp(self._now()), "verb": verb, **fields}
        with open(self.steps_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def steps(self) -> list[dict]:
        """The steps recorded so far, in order; a line that does not parse is skipped."""
        try:
            text = self.steps_path.read_text("utf-8")
        except FileNotFoundError:
            return []
        out = []
        for line in text.splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                out.append(record)
        return out

    def close(self, summary: Mapping) -> Path:
        """Write summary.md and return its path. Its first line is the restore's outcome, from `summary["outcome"]`
        ("restored", "held" or "refused"; worked out from `summary["restore"]`, the restore's reply, when absent),
        so a reader learns first whether the owner's files are back. Then the permission, the snapshot, the save,
        the country and any notes; then one table row per step (verb, outcome); then, for each `try_event` step,
        its options' table and whether every option fired and was picked."""
        lines = [_restore_line(summary.get("restore"), summary.get("outcome")), ""]
        for label, key in (("Permission", "permission"), ("Snapshot", "snapshot"), ("Save", "save"),
                           ("Country", "country"), ("Overlay removed", "overlay_removed")):
            value = summary.get(key)
            lines.append("- %s: %s" % (label, _text(value) if value not in (None, "") else "(none)"))
        for note in summary.get("notes") or ():
            lines.append("- Note: " + _text(note))
        steps = self.steps()
        lines += ["", "| # | Verb | Outcome |", "|---|---|---|"]
        for n, record in enumerate(steps, start=1):
            lines.append("| %d | %s | %s |" % (n, _cell(record.get("verb")), _cell(record.get("outcome", ""))))
        for record in steps:
            if record.get("verb") == "try_event":
                lines += ["", *_try_event_table(record)]
        self.summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.summary_path


def _outcome(restore: Mapping | None) -> str | None:
    if restore is None:
        return None
    if restore.get("held") is True:
        return "held"
    return "refused" if restore.get("refused") else "restored"


def _restore_line(restore: Mapping | None, outcome: str | None) -> str:
    outcome = outcome or _outcome(restore)
    if restore is None or outcome is None:
        return "Restore: not run. No snapshot was taken, so there was nothing of the owner's to put back."
    if outcome == "held":
        return ("Restore: HELD (%s). Nothing was put back: only the owner resolves a hold "
                "(`python3 -m game_qa held` lists it)." % _text(restore.get("reason") or "no reason given"))
    if outcome == "refused":
        detail = restore.get("detail")
        return "Restore: REFUSED (%s). The snapshot is not finished.%s" % (
            _text(restore.get("refused") or "no reason given"), " " + _text(detail) if detail else "")
    restored, removed = restore.get("restored") or [], restore.get("removed") or []
    reason = restore.get("reason")
    return "Restore: restored (%d files put back, %d removed)%s." % (
        len(restored), len(removed), "; " + _text(reason) if reason else "")


def _try_event_table(record: Mapping) -> list[str]:
    """A try-event check: its heading, that the options share one game, a row per option, and the verdict."""
    setup = record.get("setup")
    rows = record.get("options") or []
    out = ["## try-event %s%s" % (_text(record.get("event")), " (setup %s)" % _text(setup) if setup else ""), "",
           "State is shared between options: each ran on the game the one before left%s; console `event` ignores "
           "the trigger and the cooldown." % (", the setup re-run first" if setup else ""), "",
           "| Option | Fired | Before | After | Picked | New errors |", "|---|---|---|---|---|---|"]
    for row in rows:
        fired = "yes" if row.get("fired") else "did not fire" if row.get("did_not_fire") else "no"
        picked = row.get("picked")
        out.append("| %s | %s | %s | %s | %s | %d |" % (
            _cell(row.get("index")), fired, _cell(_reads(row.get("before"))), _cell(_reads(row.get("after"))),
            "option %s" % _cell(picked.get("index")) if isinstance(picked, Mapping) else "",
            len(row.get("new_errors") or [])))
    out += ["", _verdict(record, rows)]
    if any(row.get("new_errors") for row in rows):
        out.append("The new errors' lines are in %s (the try_event step's `options`)." % STEPS_FILE)
    return out


def _reads(reads) -> str:
    return "; ".join("%s = %s" % (_text(r.get("expr")), _read_value(r)) for r in reads or () if isinstance(r, Mapping))


def _read_value(read: Mapping) -> str:
    raw = str(read.get("raw") or "").split("\n")[0].strip()
    if not read.get("ok"):
        return "refused (%s)" % raw
    value = read.get("value")
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return "%g" % value
    return raw


def _verdict(record: Mapping, rows) -> str:
    outcome = record.get("outcome", "ok")
    if outcome != "ok":
        detail = record.get("detail")
        return "Not a pass: it ended on %s%s." % (_text(outcome), " (%s)" % _text(detail) if detail else "")
    if record.get("complete") is True:
        return "Every option fired and was picked."
    did_not = [str(row.get("index")) for row in rows if row.get("did_not_fire")]
    if did_not:
        return "Not a pass: option %s did not fire." % ", ".join(did_not)
    return "Not a pass: not every option fired and was picked."


def _text(value) -> str:
    return " ".join(str(value).split())


def _cell(value) -> str:
    return _text("" if value is None else value).replace("|", "\\|")
