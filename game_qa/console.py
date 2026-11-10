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
    its *arrival*: the file changes and the text is among the lines it gained.
    But (verified live on 2026-11-10) the file does not gain a line when the
    same command is entered twice running. So for a text the history already
    holds, a short wait that sees no change is "cannot tell", and the proof
    that it arrived has to come from the log: the log proof for repeats is
    required, not optional. (Whether a repeat that is not the last entry is
    written is not known; the code needs no answer to that.)
  * `debug.log` gets `Running console command:` and one `console_success:` or
    `console_failure:` line per reply line, but block-buffered: they are not in
    the file until about 4 KB more has been logged. `help ndefines.ngui` prints
    about 500 lines, so typing it after a command pushes the command's lines
    out (the flush's own `Running console command:` line comes out with them).
    A debugger trigger evaluation floods `debug.log` across several of its
    generations (verified live on 2026-11-10), so lines can be lost while a
    reply is awaited: `logtail` marks the loss and `run` raises `log_gap`.
  * A game stalled by a heavy pulse takes keys seconds late, in order. Giving up
    on a typing and typing again would run the command twice, and pressing the
    console key would close a console that was open all along. So the waits
    hold their clock while the window is not responding, and before any
    retyping and before the console key, the history (or the log) is looked at
    once more for the first typing.

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
from game_qa.logtail import GAP_MARKER, LogFollower, Parsed, parse

SCAN_CONSOLE, SCAN_ENTER = 0x29, 0x1C
SCAN_BACKSPACE = 0x0E
FLUSH_COMMAND = "help ndefines.ngui"
PROBE_COMMAND = "select_event_option list"
PERSON_IDLE_MS, FOREGROUND_WAIT_S = 30_000, 120.0

UNRESPONSIVE_S = 10.0           # a window that does not respond this long is a game that is gone
ARRIVAL_S = 5.0                 # how long a command gets to show up in the history
PROBE_ARRIVAL_S = 6.0           # the same for the probe that asks whether the console is open. Longer than the
                                # ~5 s after which Windows reports a window as not responding (the waits then hold
                                # their clock), so a slow game is never taken for a closed console and toggled shut
REPEAT_ARRIVAL_S = 1.5          # the same for a text the history already holds: a write is at once, so no
                                # change by now is a history that does not repeat entries
CONSOLE_SETTLE_S = 0.5          # after the console key, before typing into it (unverified: a guess at the animation)
POLL_S = 0.2                    # between looks at the history and the log
FOREGROUND_POLL_S = 1.0         # between looks at who has the foreground
HISTORY_TRIES = 4               # reads of the history file before it counts as unreadable
HISTORY_RETRY_S = 0.1           # between those reads
CLEAR_BACKSPACES = 64           # more than any command typed here is long


class ConsoleError(Exception):
    """`code` is one of bad_text, not_foreground, no_ack, no_reply, game_gone, stranded_text,
    history_unreadable, log_gap, or `helper: <code>` for an error of the helper itself.

    `entered` is True when the command is known to have been entered (its arrival was seen) before the
    error: a caller must not run it again.
    """

    def __init__(self, code: str, detail: str = "", entered: bool = False) -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail, self.entered = code, detail, entered


@dataclass
class Reply:
    command: str
    ok: bool | None                 # False if any reply line was a failure; None if there was none, or none was asked for
    lines: list[str]


@dataclass
class _Typed:
    """One typing of a command: what the history held just before, to tell what it gained since."""
    key: str                        # the text, stripped
    before: list[str]
    repeat: bool                    # the history already held the text


class Console:
    def __init__(self, helper: Helper, proc: ProcId, history: Path, log: LogFollower,
                 sleep=time.sleep, clock=time.monotonic) -> None:
        self._helper, self._proc, self._history_path, self._log = helper, proc, Path(history), log
        self._sleep, self._clock = sleep, clock
        self._seen: list[Parsed] = []       # console lines of the log since the current call began
        self._gap = False                   # the log lost lines since the current call began
        self._stranded = False              # text went out without its Enter: the input line holds half a command

    # ---- public

    def ensure_open(self, timeout: float = 30.0) -> None:
        """Return once the console takes commands. An open console is never toggled: only a probe that does
        not arrive, and did not turn up late either, makes it press the console key."""
        self._refuse_if_stranded()
        self._drop_log()
        self._open_console(timeout)

    def clear_line(self) -> None:
        """Empty the console's input line with Backspaces, after the usual foreground check, and allow typing
        again after a `stranded_text`. Nothing calls this by itself: whether to is the caller's decision."""
        self._keys([{"scan": SCAN_BACKSPACE} for _ in range(CLEAR_BACKSPACES)])
        self._stranded = False

    def run(self, text: str, reply: bool = True, timeout: float = 30.0) -> Reply:
        """Enter `text` as a console command and confirm that it arrived; with `reply`, also return what the
        game answered, within `timeout` seconds. (The flush command has no answer worth returning.)

        What it decides, from what it sees. It types a command once, retypes it once at most, and not at
        all if the first typing turns up late; it retypes only after making sure the console is open.

            after typing, the history       then
            gained the text, in 5 s         arrived; with a reply wanted, type the flush and wait for the log
            did not, and the text was new   not arrived: ensure the console is open; look again; retype once;
                                            still nothing: no_ack
            did not, text was already in it cannot tell: type the flush; the text's line followed directly
                                            by the flush's line in the log is the proof; none: as above
            the window is not responding    the wait's clock is held (for 10 s, then game_gone)
            gained the text later           (checked before the console key and before any retype) arrived
            Enter refused with text typed   stranded_text until `clear_line()`
        """
        if not text.strip() or "\n" in text or "\r" in text:
            raise ConsoleError("bad_text", "a console command is one non-blank line")
        self._refuse_if_stranded()
        is_flush = text.strip() == FLUSH_COMMAND
        reply = reply and not is_flush
        self._drop_log()
        text_t: _Typed | None = None
        proved = False                      # the history showed `text` arrive (possibly late)
        flushed = False                     # the flush has been typed and not been refused
        found: list[Parsed] | None = None   # its reply lines, once the log has shown them

        def landed_late() -> bool:
            if proved or found is not None or text_t is None:
                return False
            return self._landed(text_t) or self._pair(text, adjacent=True) is not None

        try:
            for attempt in (1, 2):
                ok = True
                if text_t is not None and not proved and found is None:
                    # A retry: the first typing may have been taken while the console was being sorted out.
                    proved = self._landed(text_t)
                    found = None if proved else self._pair(text, adjacent=True)
                if not proved and found is None:
                    text_t = self._type(text)
                    seen = self._watch(text_t, ARRIVAL_S)
                    proved, ok = seen is True, seen is not False
                # The flush is what makes the game write its log out: wanted for a reply, and needed as the only
                # proof of a command that the history cannot show. A flush that is typed twice does no harm.
                if ok and found is None and not is_flush and not flushed and (reply or not proved):
                    flushed = self._watch(self._type(FLUSH_COMMAND), ARRIVAL_S) is not False
                    ok = flushed or attempt == 2        # unseen twice: leave it to the log's word
                if ok and not proved and found is None:
                    found = self._await_reply(text, ARRIVAL_S if attempt == 1 else timeout, adjacent=True)
                    ok = found is not None
                if ok:
                    break
                if attempt == 1:
                    self._open_console(already=landed_late)
            else:
                raise ConsoleError("no_ack", "%r did not reach the console" % text)
            if not reply:
                return Reply(text, None, [])
            if found is None:
                found = self._await_reply(text, timeout)
            if found is None:
                raise ConsoleError("no_reply", "no answer to %r in the log within %g s" % (text, timeout))
        except ConsoleError as e:
            if proved or found is not None:
                e.entered = True
            raise
        lines = [p.text for p in found]
        verdict = False if any(p.kind == "failure" for p in found) else (True if lines else None)
        return Reply(text, verdict, lines)

    # ---- keys

    def _call(self, fn, *args):
        """A call of the helper, its errors as `ConsoleError("helper: <code>")`."""
        try:
            return fn(*args)
        except HelperError as e:
            raise ConsoleError("helper: " + e.code, e.detail) from e

    def _require_window(self) -> Window:
        win = self._call(self._helper.window, self._proc.pid)
        if not win.exists:
            raise ConsoleError("game_gone", "the game's window is gone")
        return win

    def _refuse_if_stranded(self) -> None:
        if self._stranded:
            raise ConsoleError("stranded_text", "half a command is still in the console's input line; "
                                                "clear_line() empties it")

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
                if self._call(self._helper.idle_ms) >= PERSON_IDLE_MS:
                    if self._call(self._helper.focus, self._proc.pid):
                        return
                    raise ConsoleError("not_foreground", "the game's window would not come to the front")
                if now - started >= FOREGROUND_WAIT_S:
                    raise ConsoleError("not_foreground", "someone has used the machine for %g s" % FOREGROUND_WAIT_S)
            self._sleep(FOREGROUND_POLL_S)

    def _keys(self, steps: list[dict]) -> None:
        """Send `steps` with the game in front; the one place that calls `helper.keys`.

        A refusal because the window left the front is tried once more, but only if the helper says none of
        the steps went out. If some did and one of them was text, the input line holds half a command: the
        next call is refused (`stranded_text`) rather than glued onto it.
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
                    raise ConsoleError("helper: " + e.code, e.detail) from e
                self._require_window()          # a window that is gone is game_gone, whatever was typed
                nothing_sent = e.reply.get("steps_done") == 0 and not e.reply.get("chars_sent")
                if not nothing_sent and any("text" in step for step in steps):
                    self._stranded = True
                if attempt == 2 or not nothing_sent:
                    raise ConsoleError("not_foreground", "the game's window left the front while typing") from e

    # ---- history and log

    def _read_history(self, tries: int = 1) -> list[str] | None:
        """The history's lines; none yet is an empty history, a file that cannot be read is None."""
        for n in range(tries):
            try:
                raw = self._history_path.read_bytes()
            except FileNotFoundError:
                return []
            except OSError:
                if n + 1 < tries:
                    self._sleep(HISTORY_RETRY_S)
                continue
            lines = raw.decode("utf-8-sig", errors="replace").split("\n")
            if lines and lines[-1] == "":
                lines.pop()
            return [line.rstrip("\r") for line in lines]
        return None

    def _history(self) -> list[str]:
        """The snapshot taken before typing: a read error is no news of an empty history."""
        lines = self._read_history(HISTORY_TRIES)
        if lines is None:
            raise ConsoleError("history_unreadable", "%s could not be read" % self._history_path)
        return lines

    def _drop_log(self) -> None:
        """Forget the log up to now: only lines written from here on can answer what is typed next."""
        self._log.poll()
        self._seen = []
        self._gap = False

    def _read_log(self) -> None:
        for line in self._log.poll():
            if line == GAP_MARKER:
                self._gap = True
                continue
            parsed = parse(line)
            if parsed.kind in ("command", "success", "failure"):
                self._seen.append(parsed)

    def _find_reply(self, text: str, adjacent: bool = False) -> list[Parsed] | None:
        """The reply lines of the newest run of `text` in the log so far, once a flush after it is in too.

        Newest, because the same text may have run before; the reply is what follows it up to the next
        command, which leaves out the tail of an earlier flush's output (that comes before it). With
        `adjacent` the next command must be the flush itself: that is the proof that this typing ran, since a
        flush typed for some other purpose (the probe's) must not vouch for an older line of the same text
        that was still waiting in the game's buffer.
        """
        want = text.strip()
        seen = self._seen
        newest = next((i for i in range(len(seen) - 1, -1, -1)
                       if seen[i].kind == "command" and seen[i].text.strip() == want), None)
        if newest is None:
            return None
        if want == FLUSH_COMMAND:
            return []                           # its own line is all that is wanted of it
        commands = [i for i in range(newest + 1, len(seen)) if seen[i].kind == "command"]
        flushes = [i for i in commands if seen[i].text.strip() == FLUSH_COMMAND]
        if not flushes or (adjacent and flushes[0] != commands[0]):
            return None
        return seen[newest + 1:commands[0]]

    def _pair(self, text: str, adjacent: bool = False) -> list[Parsed] | None:
        """One look at the log for `text` and its flush."""
        self._read_log()
        return self._find_reply(text, adjacent)

    def _await_reply(self, text: str, seconds: float, adjacent: bool = False) -> list[Parsed] | None:
        found: list[list[Parsed]] = []

        def shown() -> bool:
            self._read_log()
            if self._gap:
                raise ConsoleError("log_gap", "the log lost lines while waiting for the answer to %r" % text)
            reply = self._find_reply(text, adjacent)
            if reply is not None:
                found.append(reply)
            return reply is not None
        return found[0] if self._wait(shown, seconds) else None

    def _wait(self, done: Callable[[], bool], seconds: float) -> bool:
        """Poll `done` for up to `seconds`. The game's window disappearing ends the wait at once; while it
        does not respond the game is busy, not deaf, so the clock is held (up to `UNRESPONSIVE_S`)."""
        last = self._clock()
        end = last + seconds
        stuck_since: float | None = None
        while True:
            if done():
                return True
            win = self._require_window()
            now = self._clock()
            if win.responding:
                stuck_since = None
            else:
                stuck_since = now if stuck_since is None else stuck_since
                if now - stuck_since >= UNRESPONSIVE_S:
                    raise ConsoleError("game_gone", "the game has not responded for %g s" % UNRESPONSIVE_S)
                end += now - last
            last = now
            if now >= end:
                return False
            self._sleep(POLL_S)

    # ---- typing

    def _type(self, text: str) -> _Typed:
        """Type `text` and Enter. The history is read first, and a history that cannot be read stops it here."""
        before = self._history()
        key = text.strip()
        typed = _Typed(key, before, key in [line.strip() for line in before])
        self._keys([{"text": text}, {"scan": SCAN_ENTER}])
        return typed

    def _landed(self, typed: _Typed) -> bool:
        """The history has gained the text since just before it was typed (not only as its last line: a later
        typing, such as a probe, may have landed after it). A read that fails is no evidence."""
        now = self._read_history()
        if now is None or now == typed.before:
            return False
        gained = now[len(typed.before):] if now[:len(typed.before)] == typed.before else now[-1:]
        return any(line.strip() == typed.key for line in gained)

    def _watch(self, typed: _Typed, wait: float) -> bool | None:
        """True if the typing lands within `wait` seconds. If not: None when the history already held the
        text (it may not write a repeat, so this proves nothing about the console), False when it did not (the
        text did not arrive)."""
        if self._wait(lambda: self._landed(typed), min(wait, REPEAT_ARRIVAL_S) if typed.repeat else wait):
            return True
        return None if typed.repeat else False

    def _console_answers(self, probes: list[_Typed]) -> bool:
        """Type the probe and see whether the console took it."""
        typed = self._type(PROBE_COMMAND)
        probes.append(typed)
        arrival = self._watch(typed, PROBE_ARRIVAL_S)
        if arrival is not None:
            return arrival
        # A probe the history already held shows nothing there, and guessing "closed" would press the key
        # and close an open console. A flush makes the game log the probe and itself instead.
        self._type(FLUSH_COMMAND)
        return self._await_reply(PROBE_COMMAND, PROBE_ARRIVAL_S, adjacent=True) is not None

    def _open_console(self, timeout: float = 30.0, already: Callable[[], bool] | None = None) -> None:
        """Make the console take commands. `already` says whether what the caller typed has since landed: the
        game was slow, the console is open, and the key must not be pressed."""
        probes: list[_Typed] = []

        def landed_late() -> bool:
            return any(self._landed(typed) for typed in probes) or (already is not None and already())

        end = self._clock() + timeout
        while True:
            if landed_late() or self._console_answers(probes) or landed_late():
                return
            if self._clock() >= end:
                raise ConsoleError("no_ack", "the console took no command within %g s" % timeout)
            self._keys([{"scan": SCAN_CONSOLE}])
            self._sleep(CONSOLE_SETTLE_S)
