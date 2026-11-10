"""Type a command into the game's debug console, and prove that it ran.

The helper can press keys; this module decides when it may and what counts as
an answer. Two rules come before everything else: never send a key unless the
game's window is in front (`_front`), and never take the foreground from a
person who is using the machine (someone is, if there was input the helper did
not send within `PERSON_IDLE_MS`).

What the game shows of a command (verified on 2026-11-10):

  * With the console open, typed text plus Enter is a command and the console
    key (scancode 0x29) toggles it; closed, typed text does nothing. So the
    console is never opened by pressing the key blindly: a harmless probe
    command is typed first, and only if it does not arrive is the key pressed.
  * Each command entered is added to `console_history.txt` at once. That is
    its *arrival*: the file changes and the text is its new last line. Whether
    the history also writes a command it already holds is not known yet (the
    harness's first live run settles it), so for a text it already holds, a
    short wait that sees no change is "cannot tell", and the log answers.
  * `debug.log` gets `Running console command:` and one `console_success:` or
    `console_failure:` line per reply line, but block-buffered: they are not in
    the file until about 4 KB more has been logged. `help ndefines.ngui` prints
    about 500 lines, so typing it after a command pushes the command's lines
    out (the flush's own `Running console command:` line comes out with them).

`Console` consumes the `LogFollower` it is given: a line it has polled is not
returned to anyone else who polls the same follower.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from game_qa.gate import ProcId
from game_qa.helper import Helper, HelperError, Window
from game_qa.logtail import LogFollower, Parsed, parse

SCAN_CONSOLE, SCAN_ENTER = 0x29, 0x1C
FLUSH_COMMAND = "help ndefines.ngui"
PROBE_COMMAND = "select_event_option list"
PERSON_IDLE_MS, FOREGROUND_WAIT_S = 30_000, 120.0

UNRESPONSIVE_S = 10.0           # a window that does not respond this long is a game that is gone
ARRIVAL_S = 5.0                 # how long a command gets to show up in the history
PROBE_ARRIVAL_S = 3.0           # the same for the probe that asks whether the console is open
REPEAT_ARRIVAL_S = 1.5          # the same for a text the history already holds: a write is at once, so no
                                # change by now may be a history that does not repeat entries
CONSOLE_SETTLE_S = 0.5          # after the console key, before typing into it (unverified: a guess at the animation)
POLL_S = 0.2                    # between looks at the history and the log
FOREGROUND_POLL_S = 1.0         # between looks at who has the foreground


class ConsoleError(Exception):
    """`code` is one of bad_text, not_foreground, no_ack, no_reply, game_gone."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail = code, detail


@dataclass
class Reply:
    command: str
    ok: bool | None                 # False if any reply line was a failure; None if there was none, or none was asked for
    lines: list[str]


class Console:
    def __init__(self, helper: Helper, proc: ProcId, history: Path, log: LogFollower,
                 sleep=time.sleep, clock=time.monotonic) -> None:
        self._helper, self._proc, self._history_path, self._log = helper, proc, Path(history), log
        self._sleep, self._clock = sleep, clock
        self._seen: list[Parsed] = []       # console lines of the log since the current call began

    # ---- public

    def ensure_open(self, timeout: float = 30.0) -> None:
        """Return once the console takes commands. An open console is never toggled: only a probe that does
        not arrive makes it press the console key."""
        self._drop_log()
        self._open_console(timeout)

    def run(self, text: str, reply: bool = True, timeout: float = 30.0) -> Reply:
        """Enter `text` as a console command and confirm that it arrived; with `reply`, also return what the
        game answered, within `timeout` seconds. (The flush command has no answer worth returning.)"""
        if not text.strip() or "\n" in text or "\r" in text:
            raise ConsoleError("bad_text", "a console command is one non-blank line")
        is_flush = text.strip() == FLUSH_COMMAND
        reply = reply and not is_flush
        self._drop_log()
        proved = False                      # the history showed `text` arrive
        found: list[Parsed] | None = None   # its reply lines, once the log has shown them
        start = 0                           # log lines before this index are older than the current typing
        for attempt in (1, 2):
            arrived = True
            if not proved:
                seen = self._enter(text)
                proved, arrived = seen is True, seen is not False
            # The flush is what makes the game write its log out: wanted for a reply, and needed as the only
            # proof of a command that the history cannot show.
            if arrived and not is_flush and (reply or not proved):
                arrived = self._enter(FLUSH_COMMAND) is not False
            if arrived and not proved:
                found = self._await_reply(text, ARRIVAL_S if attempt == 1 else timeout, start)
                arrived = found is not None
            if arrived:
                break
            if attempt == 1:
                self._open_console()
                if not proved:
                    start = len(self._seen)     # the probe's own flush must not pair with an older line
        else:
            raise ConsoleError("no_ack", "%r did not reach the console" % text)
        if not reply:
            return Reply(text, None, [])
        if found is None:
            found = self._await_reply(text, timeout, start)
        if found is None:
            raise ConsoleError("no_reply", "no answer to %r in the log within %g s" % (text, timeout))
        lines = [p.text for p in found]
        ok = False if any(p.kind == "failure" for p in found) else (True if lines else None)
        return Reply(text, ok, lines)

    # ---- keys

    def _require_window(self) -> Window:
        win = self._helper.window(self._proc.pid)
        if not win.exists:
            raise ConsoleError("game_gone", "the game's window is gone")
        return win

    def _front(self) -> None:
        """Return only with the game's window responding and in front.

        Someone at the machine is waited for (up to `FOREGROUND_WAIT_S`) rather than interrupted; with
        nobody there the window is brought forward.
        """
        started = self._clock()
        stuck_since: float | None = None
        while True:
            win = self._require_window()
            now = self._clock()
            if not win.responding:
                stuck_since = now if stuck_since is None else stuck_since
                if now - stuck_since >= UNRESPONSIVE_S:
                    raise ConsoleError("game_gone", "the game has not responded for %g s" % UNRESPONSIVE_S)
            else:
                stuck_since = None
                if win.foreground:
                    return
                if self._helper.idle_ms() >= PERSON_IDLE_MS:
                    if self._helper.focus(self._proc.pid):
                        return
                    raise ConsoleError("not_foreground", "the game's window would not come to the front")
                if now - started >= FOREGROUND_WAIT_S:
                    raise ConsoleError("not_foreground", "someone has used the machine for %g s" % FOREGROUND_WAIT_S)
            self._sleep(FOREGROUND_POLL_S)

    def _keys(self, steps: list[dict]) -> None:
        """Send `steps` with the game in front; the one place that calls `helper.keys`.

        A refusal because the window left the front is tried once more, but only if the helper says none of
        the steps went out: a half-typed command would get the next one glued to it.
        """
        for attempt in (1, 2):
            self._front()
            try:
                self._helper.keys(self._proc.pid, steps)
                return
            except HelperError as e:
                if e.code == "bad_text":
                    raise ConsoleError("bad_text", e.detail) from e
                if e.code != "not_foreground":
                    raise
                self._require_window()          # a window that is gone is game_gone, whatever was typed
                nothing_sent = e.reply.get("steps_done") == 0 and not e.reply.get("chars_sent")
                if attempt == 2 or not nothing_sent:
                    raise ConsoleError("not_foreground", "the game's window left the front while typing") from e

    # ---- history and log

    def _history(self) -> list[str]:
        try:
            raw = self._history_path.read_bytes()
        except OSError:
            return []
        lines = raw.decode("utf-8-sig", errors="replace").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        return [line.rstrip("\r") for line in lines]

    def _drop_log(self) -> None:
        """Forget the log up to now: only lines written from here on can answer what is typed next."""
        self._log.poll()
        self._seen = []

    def _read_log(self) -> None:
        for line in self._log.poll():
            parsed = parse(line)
            if parsed.kind in ("command", "success", "failure"):
                self._seen.append(parsed)

    def _find_reply(self, text: str, start: int = 0) -> list[Parsed] | None:
        """The reply lines of the newest run of `text` in `_seen[start:]`, once the flush after it is in too.

        Newest, because the same text may have run before; the reply is what follows it up to the next
        command, which leaves out the tail of an earlier flush's output (that comes before it).
        """
        want = text.strip()
        seen = self._seen
        newest = next((i for i in range(len(seen) - 1, start - 1, -1)
                       if seen[i].kind == "command" and seen[i].text.strip() == want), None)
        if newest is None:
            return None
        if want == FLUSH_COMMAND:
            return []                           # its own line is all that is wanted of it
        commands = [i for i in range(newest + 1, len(seen)) if seen[i].kind == "command"]
        if not any(seen[i].text.strip() == FLUSH_COMMAND for i in commands):
            return None
        return seen[newest + 1:commands[0]]

    def _await_reply(self, text: str, seconds: float, start: int = 0) -> list[Parsed] | None:
        found: list[list[Parsed]] = []

        def shown() -> bool:
            self._read_log()
            reply = self._find_reply(text, start)
            if reply is not None:
                found.append(reply)
            return reply is not None
        return found[0] if self._wait(shown, seconds) else None

    def _wait(self, done: Callable[[], bool], seconds: float) -> bool:
        """Poll `done` for up to `seconds`; the game's window disappearing ends the wait at once."""
        end = self._clock() + seconds
        while True:
            if done():
                return True
            self._require_window()
            if self._clock() >= end:
                return False
            self._sleep(POLL_S)

    # ---- typing

    def _enter(self, text: str, wait: float = ARRIVAL_S) -> bool | None:
        """Type `text` and Enter. True if the history changes and ends with it within `wait` seconds. If not:
        None when the history already held the text (it may not write a repeat, so this proves nothing about
        the console), False when it did not (the text did not arrive)."""
        key = text.strip()
        before = self._history()
        repeat = key in [line.strip() for line in before]
        self._keys([{"text": text}, {"scan": SCAN_ENTER}])

        def arrived() -> bool:
            now = self._history()
            return now != before and bool(now) and now[-1].strip() == key
        if self._wait(arrived, min(wait, REPEAT_ARRIVAL_S) if repeat else wait):
            return True
        return None if repeat else False

    def _console_answers(self) -> bool:
        """Type the probe and see whether the console took it."""
        start = len(self._seen)
        arrival = self._enter(PROBE_COMMAND, PROBE_ARRIVAL_S)
        if arrival is not None:
            return arrival
        # A probe the history already held shows nothing there, and guessing "closed" would press the key
        # and close an open console. A flush makes the game log the probe and itself instead.
        self._enter(FLUSH_COMMAND, 0)
        return self._await_reply(PROBE_COMMAND, PROBE_ARRIVAL_S, start) is not None

    def _open_console(self, timeout: float = 30.0) -> None:
        end = self._clock() + timeout
        while True:
            if self._console_answers():
                return
            if self._clock() >= end:
                raise ConsoleError("no_ack", "the console took no command within %g s" % timeout)
            self._keys([{"scan": SCAN_CONSOLE}])
            self._sleep(CONSOLE_SETTLE_S)
