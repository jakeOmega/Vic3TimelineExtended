"""Type a command into the game's debug console, and prove that it ran.

The helper can press keys; this module decides when it may and what counts as
an answer. Two rules come before everything else: never send a key unless the
game's window is in front (`_front`), and never take the foreground from a
person who is using the machine (someone is, if the cursor moved or the
foreground window changed between two presence readings `PRESENCE_GAP_S` apart;
the helper's own cursor move is not a person; the foreground is taken back only
after `QUIET_GAPS` such gaps in a row show no change).

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
    written is not known; the code needs no answer to that.) The encodings of the history
    file and of the log are not verified either, so a command with a non-ASCII character
    is refused (`bad_text`): if neither echoed it as typed, nothing could prove that it
    arrived, and it would be typed twice.
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

Windows' idle time says nothing here: with a remote-desktop session connected it reads 0 to 31 ms
continuously (measured on the owner's machine, 2026-11-10), so a rule on it never lets the console
take the foreground back. Presence is read from the cursor and the foreground window instead: a
gap is quiet if two readings a gap apart show the same foreground window and a cursor that did not
move, or sits exactly where the helper last put it (a click); after `QUIET_GAPS` quiet gaps in a row
(about 6 s) the foreground is taken back, and any change restarts the count. A person who keeps the
cursor moving or the windows changing is waited for, up to `FOREGROUND_WAIT_S`, and then the step fails
with `not_foreground`, nothing typed. The rule's known limit: someone using the keyboard alone, or
reading, with the mouse still and the same window in front, changes neither signal, so after those
two gaps they are read as nobody and the game's window is brought forward over them.

The console is known to be open after a round trip and known to be closed after `close()`; `run` and
`send` open one that is known closed, `send` also one that is not known to be open (it has no retry
of its own), and `close()` and `hotkey()` act only on what is known.

A click takes the keyboard (live, 2026-11-12): after a click into the script profiler, a command typed
next never reached the console, and a click on the console's input line gave the keyboard back. What
would happen to a probe typed then is the trouble: its letters and Enter go to whatever took the
keyboard (a tool window's search field, or the game's own keys, where a space toggles the pause), and
when it does not arrive the console key is pressed, which may close the open console. So a click made
while the console is known open (`clicked()`) latches `keyboard_away`: every method that sends a key
refuses `keyboard_away` with `entered` False, before any key, until `take_keyboard_back()`, called
after a click on the console's input line, has typed one probe and seen it arrive. It never presses
the console key. A click while the console is known closed, or not known, leaves the state as it is.

`Console` consumes the `LogFollower` it is given: a line it has polled is not
returned to anyone else who polls the same follower.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from game_qa.gate import ProcId
from game_qa.helper import Helper, HelperError, Presence, Window
from game_qa.logtail import GAP_MARKER, LogFollower, Parsed, parse

SCAN_CONSOLE, SCAN_ENTER = 0x29, 0x1C
SCAN_BACKSPACE = 0x0E
FLUSH_COMMAND = "help ndefines.ngui"
PROBE_COMMAND = "select_event_option list"
FOREGROUND_WAIT_S = 120.0
PRESENCE_GAP_S = 3.0            # between the two readings that say whether someone is at the machine
QUIET_GAPS = 2                  # quiet gaps in a row before the foreground is taken back

UNRESPONSIVE_S = 10.0           # a window that does not respond this long is a game that is gone
ARRIVAL_S = 5.0                 # how long a command gets to show up in the history
PROBE_ARRIVAL_S = 6.0           # the same for the probe that asks whether the console is open. Longer than the
                                # ~5 s after which Windows reports a window as not responding (the waits then hold
                                # their clock), so a slow game is never taken for a closed console and toggled shut
REPEAT_ARRIVAL_S = 1.5          # the same for a text the history already holds: a write is at once, so no
                                # change by now is a history that does not repeat entries
CONSOLE_SETTLE_S = 0.5          # after the console key, before typing into it (unverified: a guess at the animation)
POLL_S = 0.2                    # between looks at the history and the log
FOREGROUND_POLL_S = 1.0         # between looks at a window that does not respond
HISTORY_TRIES = 4               # reads of the history file before it counts as unreadable
HISTORY_RETRY_S = 0.1           # between those reads
CLEAR_BACKSPACES = 64           # more than any command typed here is long


KEYBOARD_AWAY = ("a click since the console last answered may have given the keyboard to another window (a tool "
                 "window such as the script profiler), so nothing was typed. `python3 -m game_qa click --console` "
                 "clicks the console's input line and proves the keyboard is back")


class ConsoleError(Exception):
    """`code` is one of bad_text, not_foreground, no_ack, no_reply, game_gone, stranded_text,
    history_unreadable, log_gap, console_open (`hotkey` while the console is not known to be closed),
    console_not_open (`close` while it is not known to be open), keyboard_away (a key while a click may
    have taken the keyboard), or `helper: <code>` for an error of the helper itself.

    `entered` says whether the command was entered, and only False allows a caller to run it again:

      * True: its arrival was seen before the error. Do not run it again.
      * False: no Enter for it was ever sent, or it was typed and watched for and never arrived (`no_ack`).
      * None: an Enter for it went out (or may have: the helper failed without saying how far it got) and
        nothing proves either way, for instance because the error came while the console was being sorted
        out after a slow game, or the log lines that would have shown it are lost (`log_gap`). It may have
        run, or may still run: do not retry it as you would on False.
    """

    def __init__(self, code: str, detail: str = "", entered: bool | None = False) -> None:
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


def _someone_between(before: Presence, after: Presence) -> bool:
    """Whether two readings show that a person was at the machine in between: the foreground window changed, or
    the cursor moved to somewhere other than where the helper put it (the later reading says where that is)."""
    if after.foreground != before.foreground:
        return True
    return after.cursor != before.cursor and after.cursor != after.helper_cursor


class Console:
    def __init__(self, helper: Helper, proc: ProcId, history: Path, log: LogFollower,
                 sleep=time.sleep, clock=time.monotonic) -> None:
        self._helper, self._proc, self._history_path, self._log = helper, proc, Path(history), log
        self._sleep, self._clock = sleep, clock
        self._seen: list[Parsed] = []       # console lines of the log since the current call began
        self._gap = False                   # the log lost lines since the current call began
        self._stranded = False              # text went out without its Enter: the input line holds half a command
        self._enter_unknown = False         # a helper error left it unknown whether an Enter went out (since run began)
        self._open: bool | None = None      # the console: True after a round trip, False after close(), None unknown
        self._sent: dict[str, _Typed] = {}  # for `arrived`: each text `send` typed, as the history stood just before
        self._keyboard_away = False         # a click while the console was open: no key until take_keyboard_back()
        self._reclaiming = False            # take_keyboard_back() is typing its probe

    # ---- public

    @property
    def keyboard_away(self) -> bool:
        """A click may have given the keyboard to another window: every key is refused until it is taken back."""
        return self._keyboard_away

    @property
    def input_line_there(self) -> bool:
        """Whether the console is open as far as is known, so that its input line is there to click: it was known
        open when the click that latched `keyboard_away` was made, or is known open now."""
        return self._keyboard_away or self._open is True

    def clicked(self) -> None:
        """A click went out, or may have, somewhere other than the console's input line. If the console was known
        open (or the keyboard already away) the keyboard is latched away and the console's state is not known any
        more; a console known closed or not known is left as it is, and found out as before."""
        if self._open is True or self._keyboard_away:
            self._keyboard_away = True
            self._open = None

    def take_keyboard_back(self) -> bool:
        """After a click on the console's input line: type the probe once (and the flush, when the history
        already holds the probe) and see whether the console took it. True: it did, the latch is lifted and the
        console is known open. False: it did not, the latch is set (whether or not it was before) and the console
        key was not pressed, since the console may well be open with the keyboard elsewhere. An error while
        probing leaves the latch set too, and is raised."""
        self._refuse_if_stranded()
        self._drop_log()
        probes: list[_Typed] = []
        self._reclaiming = True
        arrived = False
        try:
            arrived = self._console_answers(probes) or any(self._landed(typed) for typed in probes)
        finally:
            self._reclaiming = False
            self._keyboard_away = not arrived
            self._open = True if arrived else None
        return arrived

    def ensure_open(self, timeout: float = 30.0) -> None:
        """Return once the console takes commands. An open console is never toggled: only a probe that does
        not arrive, and did not turn up late either, makes it press the console key."""
        self._refuse_if_away()
        self._refuse_if_stranded()
        self._drop_log()
        self._open_console(timeout)

    def front(self) -> None:
        """Return with the game's window responding and in front, by the same presence rule as every key, without
        touching the console: for a click (`Session.click`), whose point an opened console could cover."""
        self._front()

    def clear_line(self) -> None:
        """Empty the console's input line with Backspaces, after the usual foreground check, and allow typing
        again after a `stranded_text`. Nothing calls this by itself: whether to is the caller's decision."""
        self._refuse_if_away()
        self._keys([{"scan": SCAN_BACKSPACE} for _ in range(CLEAR_BACKSPACES)])
        self._stranded = False

    def send(self, text: str) -> None:
        """Type `text` and Enter once, after the usual checks of `run` (the text, a stranded line, the foreground),
        and return without waiting: `arrived(text)` says later whether the history gained it. It never types a
        text again. A console that is not known to be open is opened first, since a send that is lost to a closed
        console cannot be told from one the game has not got to yet. A send that fails has `entered` None when an
        Enter may have gone out and False otherwise. Sending proves nothing about the console afterwards: the
        belief is what the check before typing left, and neither a send nor `arrived` changes it."""
        self._check_text(text)
        self._refuse_if_away()
        self._refuse_if_stranded()
        if self._open is not True:
            self._drop_log()
            self._open_console()
        self._enter_unknown = False             # only this typing's Enter counts, not a probe's
        try:
            self._sent[text.strip()] = self._type(text)
        except ConsoleError as e:
            if self._enter_unknown:
                e.entered = None
            raise

    def arrived(self, text: str) -> bool:
        """Whether the history has gained `text` since `send` typed it (the latest send of that text). False
        before the game has taken it, for a text `send` has not typed, and also for a text the history already
        held when it was sent and does not write again (verified live: the same command twice running adds no
        line), so False never proves that it did not run. `run` has the log's proof for those. It only reads:
        a text that arrived says the console took it then, and a `close()` since may have shut it."""
        typed = self._sent.get(text.strip())
        return typed is not None and self._landed(typed)

    def close(self) -> None:
        """Press the console key once, with the usual checks, to close a console known to be open (after a round
        trip). The closing is not proved: a later `run`, `send` or `ensure_open` finds out the state again."""
        self._refuse_if_away()
        self._refuse_if_stranded()
        if self._open is not True:
            raise ConsoleError("console_not_open", "the console is not known to be open: a command that arrived "
                                                   "or ensure_open() says so")
        self._open = None                   # until the key press is known to have gone out
        try:
            self._keys([{"scan": SCAN_CONSOLE}])
        except ConsoleError as e:
            if e.code == "not_foreground":  # refused before the key: nothing changed
                self._open = True
            raise
        self._open = False
        self._sleep(CONSOLE_SETTLE_S)           # let it finish closing before the game gets another key

    def hotkey(self, scan: int) -> None:
        """Press one key (a scancode) in the game itself, with the usual checks. With the console open the key
        would go into its input line, so this is refused unless the console is known to be closed."""
        self._refuse_if_away()
        self._refuse_if_stranded()
        if self._open is not False:
            raise ConsoleError("console_open", "the console is not known to be closed: close() it first")
        self._keys([{"scan": scan}])

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
            log lines lost while waiting    log_gap (`entered` None unless the arrival was seen)

        A text is one non-blank line of at most `CLEAR_BACKSPACES` ASCII characters.
        """
        self._check_text(text)
        self._refuse_if_away()
        self._refuse_if_stranded()
        self._enter_unknown = False
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

        if self._open is False:
            self._open_console()                # known shut: typing now would be lost
            self._enter_unknown = False         # the probe's Enter says nothing of this text, which is not typed yet
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
            self._open = True
            if not reply:
                return Reply(text, None, [])
            if found is None:
                found = self._await_reply(text, timeout)
            if found is None:
                raise ConsoleError("no_reply", "no answer to %r in the log within %g s" % (text, timeout))
        except ConsoleError as e:
            if proved or found is not None:
                self._open = True               # it arrived, so the console took it
                e.entered = True
            elif e.code == "no_ack":
                self._open = None               # a probe may have got through, but neither typing did: not known
            elif text_t is not None or self._enter_unknown:
                e.entered = None                # an Enter went out and nothing proves it either way: do not retry
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

    def _check_text(self, text: str) -> None:
        """A text is one non-blank line of at most `CLEAR_BACKSPACES` ASCII characters."""
        if not text.strip() or "\n" in text or "\r" in text:
            raise ConsoleError("bad_text", "a console command is one non-blank line")
        if not text.isascii():
            raise ConsoleError("bad_text", "a console command is ASCII: the encodings of the game's history and "
                                           "log are unverified, so a command could not be proved to have arrived")
        if len(text) > CLEAR_BACKSPACES:
            raise ConsoleError("bad_text", "a console command is at most %d characters, so that clear_line() "
                                           "can always empty what was typed" % CLEAR_BACKSPACES)

    def _refuse_if_away(self) -> None:
        if self._keyboard_away and not self._reclaiming:
            raise ConsoleError("keyboard_away", KEYBOARD_AWAY, entered=False)

    def _refuse_if_stranded(self) -> None:
        if self._stranded:
            raise ConsoleError("stranded_text", "half a command is still in the console's input line; "
                                                "clear_line() empties it")

    def _front(self) -> None:
        """Return only with the game's window responding and in front.

        Someone at the machine is waited for (up to `FOREGROUND_WAIT_S`) rather than interrupted: the window
        is brought forward only after `QUIET_GAPS` gaps in a row between presence readings show nobody there.
        The first reading of a call is taken afresh, and one from before the window stopped responding is
        dropped with the count, so a pair is always a whole gap apart.
        """
        started = self._clock()
        stuck_since: float | None = None
        previous: Presence | None = None
        quiet = 0                               # quiet gaps in a row
        while True:
            win = self._require_window()
            now = self._clock()
            if not win.responding:
                previous, quiet = None, 0
                stuck_since = now if stuck_since is None else stuck_since
                if now - stuck_since >= UNRESPONSIVE_S:
                    raise ConsoleError("game_gone", "the game has not responded for %g s" % UNRESPONSIVE_S)
                self._sleep(FOREGROUND_POLL_S)
                continue
            stuck_since = None
            if win.foreground:
                return
            reading = self._call(self._helper.presence)
            if previous is not None:
                quiet = 0 if _someone_between(previous, reading) else quiet + 1
            if quiet >= QUIET_GAPS:
                if self._call(self._helper.focus, self._proc.pid):
                    return
                raise ConsoleError("not_foreground", "the game's window would not come to the front")
            if now - started >= FOREGROUND_WAIT_S:
                raise ConsoleError("not_foreground", "someone has used the machine for %g s" % FOREGROUND_WAIT_S)
            previous = reading
            self._sleep(PRESENCE_GAP_S)

    def _keys(self, steps: list[dict]) -> None:
        """Send `steps` with the game in front; the one place that calls `helper.keys`.

        A refusal because the window left the front is tried once more, but only if the helper says none of
        the steps went out. If some did and one of them was text, the input line holds half a command: the
        next call is refused (`stranded_text`) rather than glued onto it. While the keyboard is away (a click took
        it) nothing is sent: the public methods refuse first, and this is the backstop.
        """
        self._refuse_if_away()
        for attempt in (1, 2):
            self._front()
            try:
                self._helper.keys(self._proc.pid, steps)
                return
            except HelperError as e:
                if e.code == "bad_text":
                    raise ConsoleError("bad_text", e.detail) from e
                if e.code != "not_foreground":
                    # It failed partway, and nothing says how far: the line may hold text, an Enter may have gone out.
                    if any("text" in step for step in steps):
                        self._stranded = True
                    if any(step.get("scan") == SCAN_ENTER for step in steps):
                        self._enter_unknown = True
                    raise ConsoleError("helper: " + e.code, e.detail) from e
                nothing_sent = e.reply.get("steps_done") == 0 and not e.reply.get("chars_sent")
                if not nothing_sent and any("text" in step for step in steps):
                    self._stranded = True       # before anything else can raise: the line holds half a command
                self._require_window()          # a window that is gone is game_gone, whatever was typed
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
        """One look at the log for `text` and its flush. A reply read across a gap is not a reply."""
        self._read_log()
        if self._gap:
            raise ConsoleError("log_gap", "the log lost lines while looking for the answer to %r" % text)
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
            if landed_late():
                self._open = True
                return
            self._open = None                   # until a probe arrives, whatever was believed before is not known
            if self._console_answers(probes) or landed_late():
                self._open = True
                return
            if self._clock() >= end:
                raise ConsoleError("no_ack", "the console took no command within %g s" % timeout)
            self._keys([{"scan": SCAN_CONSOLE}])
            self._sleep(CONSOLE_SETTLE_S)
