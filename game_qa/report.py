"""The run folder's record: one JSON line per step, and a summary a session reads first.

    <backup root>/runs/<snapshot id>/steps.jsonl   one object per step: its UTC time, the verb, what it found
    <backup root>/runs/<snapshot id>/summary.md    the restore's outcome first, then the run, then the mod's
                                                   self-check verdicts (every BROKEN first), then a table of the
                                                   steps, then one table per try-event check, a row per option

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


def read_steps(run_dir: Path) -> list[dict]:
    """The steps recorded in a run folder, in order; a line that does not parse (bytes that are not UTF-8
    included) is skipped, and a folder with no step record has none. Reads only: unlike `Report`, it never makes
    the folder."""
    try:
        text = (Path(run_dir) / STEPS_FILE).read_text("utf-8", errors="replace")
    except (FileNotFoundError, NotADirectoryError):
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
        return read_steps(self.dir)

    def close(self, summary: Mapping) -> Path:
        """Write summary.md and return its path. Its first line is the restore's outcome, from `summary["outcome"]`
        ("restored", "held", "refused", or "game_left_up" when restore was not run because the game may still be
        up; worked out from `summary["restore"]`, the restore's reply, when absent), so a reader learns first
        whether the owner's files are back; when the stop's reply says what to do next (`summary["next"]`), that
        line says it, word for word. Then the permission, the snapshot, the save, the country, whether the
        overlay was removed (and, when `summary["overlay_kept"]` gives a reason, why it was kept) and any notes;
        then, when `summary["self_checks"]` holds them (`selfchecks.of_run`), the run's TE_SELF_CHECK verdicts,
        every BROKEN first; then one table row per step (verb, outcome); then, for each `try_event` step, its
        options' table and whether every option fired and was picked."""
        lines = [_restore_line(summary.get("restore"), summary.get("outcome"), summary.get("snapshot"),
                               summary.get("next")), ""]
        for label, key in (("Permission", "permission"), ("Snapshot", "snapshot"), ("Save", "save"),
                           ("Country", "country"), ("Overlay removed", "overlay_removed")):
            value = summary.get(key)
            lines.append("- %s: %s" % (label, _text(value) if value not in (None, "") else "(none)"))
        if summary.get("overlay_kept"):
            lines.append("- Overlay kept: " + _text(summary["overlay_kept"]))
        for note in summary.get("notes") or ():
            lines.append("- Note: " + _text(note))
        if isinstance(summary.get("self_checks"), Mapping):
            lines += ["", *_self_checks(summary["self_checks"])]
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


def _restore_line(restore: Mapping | None, outcome: str | None, snapshot: str | None = None,
                  next_step: str | None = None) -> str:
    if outcome == "game_left_up":
        return ("Restore: NOT RUN: the game may still be up, and a restore beside it would hold. Nothing was put "
                "back. Next: %s" % (_text(next_step) if next_step else "run `python3 -m game_qa restore %s` once no "
                                    "game is running." % _text(snapshot or "<id>")))
    outcome = outcome or _outcome(restore)
    if restore is None or outcome is None:
        return "Restore: not run. No snapshot was taken, so there was nothing of the owner's to put back."
    if outcome == "held":
        # A hold can come after some files were put back (part 1 lists them in `restored` and `removed`), and
        # restore puts the owner's playset back even when it holds the rest (`playset_restored`): say what was.
        reason = _text(restore.get("reason") or "no reason given")
        restored, removed = restore.get("restored") or [], restore.get("removed") or []
        if restore.get("reason") == "retime_unverified":
            # The one hold that comes after everything is back (restore._retime): nothing waits. The reply does
            # not name the file; the journal's `held` entry does.
            return ("Restore: HELD (%s). Nothing is left to put back (%d files put back, %d removed, %d given the "
                    "snapshot's time again), but one file carries the snapshot's time over bytes that could not be "
                    "proved the snapshot's: the last `held` entry of the snapshot's journal.jsonl names it "
                    "(`files`). Look at that file first, and if its content is wanted, save it again so that its "
                    "time is no longer the snapshot's; only the owner resolves a hold (`python3 -m game_qa held` "
                    "lists it)."
                    % (reason, len(restored), len(removed), len(restore.get("retimed") or [])))
        if restore.get("reason") == "manual_save_changed":
            # The other hold that comes after everything is back (restore._manual_saves): the saves were never
            # copied, so nothing waits that the harness could put back.
            saves = restore.get("manual_saves") if isinstance(restore.get("manual_saves"), Mapping) else {}
            parts = ["%s: %s" % (label, _names(saves.get(key))) for key, label in (("changed", "changed"),
                                                                                   ("missing", "gone"))
                     if saves.get(key)]
            return ("Restore: HELD (%s). Everything the snapshot holds was put back (%d files put back, %d removed, "
                    "%d given the snapshot's time again), but the owner's own saves in save games/ differ from "
                    "the snapshot's listing (%s). No snapshot copies them, so nothing can put them back: tell the "
                    "owner which, since only the owner resolves a hold (`python3 -m game_qa held` lists it), and a "
                    "later restore of this snapshot holds again while the save differs."
                    % (reason, len(restored), len(removed), len(restore.get("retimed") or []),
                       "; ".join(parts) or "the reply's manual_saves names them"))
        if restore.get("playset_restored") is True:
            done = " (%d files put back and %d removed in all)" % (len(restored), len(removed)) if (
                len(restored) > 1 or removed) else ""
            return ("Restore: HELD (%s). content_load.json was put back%s, so the game starts with the owner's "
                    "playset again; the rest of the snapshot waits: only the owner resolves a hold "
                    "(`python3 -m game_qa held` lists it)." % (reason, done))
        left = " The run's playset is still in place." if restore.get("playset_left") else ""
        done = ("%d files were put back and %d removed before the hold; the rest waits" % (len(restored), len(removed))
                if restored or removed else "Nothing was put back")
        return ("Restore: HELD (%s). %s: only the owner resolves a hold (`python3 -m game_qa held` lists it).%s"
                % (reason, done, left))
    if outcome == "refused":
        detail = restore.get("detail")
        return "Restore: REFUSED (%s). The snapshot is not finished.%s%s" % (
            _text(restore.get("refused") or "no reason given"), " " + _text(detail) if detail else "",
            " Next: " + _text(next_step) if next_step else "")
    restored, removed = restore.get("restored") or [], restore.get("removed") or []
    reason = restore.get("reason")
    return "Restore: restored (%d files put back, %d removed)%s." % (
        len(restored), len(removed), "; " + _text(reason) if reason else "")


_VERDICT_ORDER = ("BROKEN", "START", "OK")        # as selfchecks orders the checks: every BROKEN first


def _self_checks(found: Mapping) -> list[str]:
    """The mod's TE_SELF_CHECK lines of the run (`selfchecks.of_run`): how many checks ended on each verdict,
    where the lines were read from (the session's copy of the log, and the lines kept from the run that made
    the fixture), then a row per check in the order given, which puts every BROKEN first."""
    checks = [check for check in found.get("checks") or () if isinstance(check, Mapping)]
    counts = found.get("counts") if isinstance(found.get("counts"), Mapping) else {}
    session = found.get("session") if isinstance(found.get("session"), Mapping) else {}
    fixture = found.get("fixture") if isinstance(found.get("fixture"), Mapping) else {}
    out = ["## Self-checks", ""]
    if checks:
        order = [v for v in _VERDICT_ORDER if counts.get(v)] + sorted(v for v in counts if v not in _VERDICT_ORDER)
        out.append(", ".join("%s %s%s" % (counts[v], _text(v), " (no verdict was logged after it)" if v == "START"
                                          else "") for v in order) + ".")
    else:
        out.append("No TE_SELF_CHECK line was read.")
    gaps = session.get("gaps")
    out += ["", "- Session: %s TE_SELF_CHECK lines in %s%s. The game writes its log in blocks, so a line logged "
                "after the last verb may be missing."
                % (_text(session.get("lines", 0)), _text(session.get("file") or "(no log)"),
                   "; lines were lost to the log's rotation (%s times), and a verdict logged then is not here"
                   % _text(gaps) if gaps else "")]
    if fixture.get("kept"):
        out.append("- The run that made the fixture: %s lines kept from snapshot %s, %s of them TE_SELF_CHECK (%s)."
                   % (_text(fixture.get("lines")), _text(fixture.get("snapshot")), _text(fixture.get("self_checks")),
                      _text(fixture.get("file"))))
    else:
        out.append("- The run that made the fixture: no lines (%s)."
                   % _text(fixture.get("detail") or "none were kept").rstrip("."))
    if session.get("unvouched"):
        out.append("- **The session's rows cannot be vouched for** (marked \"not vouched for\" below): %s."
                   % _text(session["unvouched"]).rstrip("."))
    if checks:
        out += ["", "| Check | Verdict | From | Line |", "|---|---|---|---|"]
        for check in checks:
            source = "%s%s" % (_text(check.get("source")), " (not vouched for)" if check.get("unvouched") else "")
            out.append("| %s | %s | %s | %s |" % (_cell(check.get("name")), _cell(check.get("verdict")),
                                                  _cell(source), _cell(check.get("line"))))
    return out


def _try_event_table(record: Mapping) -> list[str]:
    """A try-event check: its heading, that the options share one game, a row per option, and the verdict."""
    setup = record.get("setup")
    rows = record.get("options") or []
    out = ["## try-event %s%s" % (_text(record.get("event")), " (setup %s)" % _text(setup) if setup else ""), "",
           "State is shared between options: each ran on the game the one before left%s; console `event` ignores "
           "the trigger and the cooldown." % (", the setup re-run first" if setup else ""), "",
           "| Option | Fired | Before | After | Picked | New errors |", "|---|---|---|---|---|---|"]
    for row in rows:
        fired = ("yes" if row.get("fired") else "ran, not pending" if row.get("ran_not_pending") else
                 "did not fire" if row.get("did_not_fire") else "no")
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
    """A read as the game gave it: a number is its raw text (the first line), never a rounding of it, so a change
    in any digit shows (`%g` printed 21570770 and 21570790 alike); a trigger's answer is yes or no."""
    raw = str(read.get("raw") or "").split("\n")[0].strip()
    if not read.get("ok"):
        return "refused (%s)" % raw
    value = read.get("value")
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)) and not raw:
        return repr(value)
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
    ran = [str(row.get("index")) for row in rows if row.get("ran_not_pending")]
    if ran:
        return ("Not a pass: option %s ran (the console says Executed) but was never pending, so nothing was "
                "picked: a hidden event, or one that resolved at once. Its effects are not checked here."
                % ", ".join(ran))
    return "Not a pass: not every option fired and was picked."


def _text(value) -> str:
    return " ".join(str(value).split())


def _cell(value) -> str:
    return _text("" if value is None else value).replace("|", "\\|")


NAMES_SHOWN = 10        # a list of saves in the summary's first line names this many, then counts the rest


def _names(value) -> str:
    """A list of file names for a sentence: the first NAMES_SHOWN, then how many more."""
    names = [_text(name) for name in value] if isinstance(value, (list, tuple)) else [_text(value)]
    shown = ", ".join(names[:NAMES_SHOWN])
    return shown + (" and %d more" % (len(names) - NAMES_SHOWN) if len(names) > NAMES_SHOWN else "")
