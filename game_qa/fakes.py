"""Stand-ins for the Windows side, shared by the tests.

`FakeBackend` scripts the Win32 calls that `win_helper.handle` makes, so the
helper's refusals can be tested without Windows. `FakeHelper` implements the
`helper.Helper` protocol in memory for the modules above it. Their state is
plain attributes, for a test to set and read.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Sequence

from game_qa import win_helper
from game_qa.gate import ProcId
from game_qa.helper import HelperError, Window

SCAN_ENTER = 0x1C
SCAN_CONSOLE = 0x29
SCAN_BACKSPACE = 0x0E
FLUSH_COMMAND = "help ndefines.ngui"        # the command whose long output pushes the game's buffered log out
_HELP_LINES = 500                           # what it prints, about
_HELD_BACK = 120                            # the last of it that the game is still holding when the file is written


class FakeSocket:
    """The connection `connect` hands back: what was sent, and what is waiting to be received."""

    def __init__(self) -> None:
        self.sent: list[bytes] = []
        self.incoming: deque[bytes] = deque()
        self.closed = False
        self.peer_closed = False        # the other end hung up: recv returns b"" once the queue is empty
        self.send_error: Exception | None = None
        self.timeout: float | None = None
        self.timeout_at_send: list[float | None] = []      # the timeout in force at each sendall

    def sendall(self, data: bytes) -> None:
        self.timeout_at_send.append(self.timeout)
        if self.send_error is not None:
            raise self.send_error
        self.sent.append(bytes(data))

    def settimeout(self, seconds: float) -> None:
        self.timeout = seconds

    def close(self) -> None:
        self.closed = True

    def recv(self, size: int) -> bytes:
        if self.closed:
            raise OSError("socket closed")
        if self.incoming:
            return self.incoming.popleft()
        if self.peer_closed:
            return b""
        raise TimeoutError("timed out")


class FakeBackend:
    """The object `win_helper.handle` calls for everything that needs Windows.

    Times are milliseconds on one clock, `now`; `last_input` is when the system
    last saw any input, which the fake sets to `now` whenever the helper sends a
    key (or taps ALT to take the foreground), as Windows would.
    """

    def __init__(self) -> None:
        self.now = 1_000_000
        self.last_input = 900_000
        self.foreground = 70                    # the foreground window's handle
        self.other_window = 999                 # where the foreground goes when the game loses it
        self.windows: dict[int, dict] = {
            7: {"hwnd": 70, "title": "Victoria 3", "responding": True, "client": (0, 0, 1920, 1080)},
        }
        self.creation: dict[int, str] = {}      # live processes: pid -> creation time
        self.next_pid = 1000
        self.launched: list[tuple[str, list, str]] = []
        self.vanish_on_launch = False
        self.sent: list[tuple[str, object]] = []        # ("scan", n) and ("text", s), in order
        self.slept: list[int] = []
        self.on_sleep = None                    # called with the milliseconds after each sleep
        self.lose_focus_after: int | None = None        # the game loses the foreground after this many keys
        self.lose_focus_after_sleep = False
        self.focus_succeeds = True
        self.needs_alt = True                   # the plain SetForegroundWindow fails until ALT has been tapped
        self.alt_taps = 0
        self.set_foreground_calls = 0
        self.during_focus_wait = None           # called while the helper waits after a tap, for a person to "type"
        self.on_foreground_check = None         # called whenever the foreground window is looked at
        self.terminated: list[int] = []
        self.terminate_args: list[tuple[int, str]] = []
        self.terminate_result = True
        self.captured: list[tuple[int, int, int, int]] = []
        self.connected: tuple[str, int] | None = None
        self.connect_error: Exception | None = None
        self.sock = FakeSocket()

    # processes

    def create_process(self, exe: str, args: Sequence[str], cwd: str) -> int:
        self.launched.append((exe, list(args), cwd))
        pid = self.next_pid
        self.next_pid += 1
        if not self.vanish_on_launch:
            self.creation[pid] = "2026-11-10T14:00:%02d.%07dZ" % (pid % 60, pid)
            self.windows[pid] = {"hwnd": 5000 + pid, "title": "Victoria 3", "responding": True,
                                 "client": (0, 0, 1920, 1080)}
        return pid

    def creation_time(self, pid: int) -> str | None:
        return self.creation.get(pid)

    def terminate(self, pid: int, created: str) -> bool:
        self.terminate_args.append((pid, created))
        if not self.terminate_result:
            return False
        self.terminated.append(pid)
        self.creation.pop(pid, None)
        self.windows.pop(pid, None)
        return True

    # windows and input

    def window_of(self, pid: int) -> dict | None:
        win = self.windows.get(pid)
        return dict(win) if win else None

    def foreground_hwnd(self) -> int:
        if self.on_foreground_check is not None:
            self.on_foreground_check()
        return self.foreground

    def set_foreground(self, hwnd: int) -> tuple[bool, int | None]:
        """Like the real one: a plain attempt, then (only if needed) an ALT tap and a second attempt.

        Returns (in front afterwards, the tick of the ALT tap or None); a tap is input the system sees.
        """
        self.set_foreground_calls += 1
        if self.focus_succeeds and not self.needs_alt:
            self.foreground = hwnd
            return True, None
        self.alt_taps += 1
        self.last_input = self.now
        tapped_at = self.now
        self.now += 300                         # the wait after the second attempt
        if self.during_focus_wait is not None:
            self.during_focus_wait()
        if self.focus_succeeds:
            self.foreground = hwnd
        return self.foreground == hwnd, tapped_at

    def _key(self, kind: str, value: object) -> None:
        self.sent.append((kind, value))
        self.last_input = self.now
        if self.lose_focus_after is not None and len(self.sent) >= self.lose_focus_after:
            self.foreground = self.other_window

    def send_scan(self, scan: int) -> None:
        self._key("scan", scan)

    def send_text(self, text: str) -> None:
        self._key("text", text)

    def tick(self) -> int:
        return self.now

    def last_input_tick(self) -> int:
        return self.last_input

    def sleep(self, ms: int) -> None:
        self.slept.append(ms)
        self.now += ms
        if self.lose_focus_after_sleep:
            self.foreground = self.other_window
        if self.on_sleep is not None:
            self.on_sleep(ms)

    # screen and network

    def capture(self, client: tuple[int, int, int, int]) -> tuple[int, int, bytes]:
        self.captured.append(tuple(client))
        _x, _y, w, h = client
        return w, h, b"\x10\x80\xf0" * (w * h)

    def connect(self, host: str, port: int) -> FakeSocket:
        if self.connect_error is not None:
            raise self.connect_error
        self.connected = (host, port)
        return self.sock


class FakeHelper:
    """`helper.Helper` in memory: one game window, a console history file, a queue of bytes from the debugger.

    It refuses what the real helper refuses (keys while the game is not in
    front, typed text with a line break), so code under test meets the same errors.

    It also imitates the console as seen in the real game. The console key
    (scancode 0x29) toggles `console_open`; typed text plus Enter is a command
    only while it is open, and then goes into the history file at once. Each
    command the game runs is logged as a `Running console command:` line and
    the lines given to `on`, but `debug.log` is block-buffered: the lines wait in
    `unwritten` until a `help ndefines.ngui` is entered, which writes them all,
    its own line and most of its long output too (the tail stays buffered).
    `now` is a fake clock for code under test: `sleep` moves it, nothing else does.

    A stalled game (a monthly pulse can hold it for seconds) is `latency`: each key the
    helper sends is taken by the game that many fake seconds later, in order, and
    until then the history and the log show nothing of it. With `busy_while_late` the
    window also reports not responding while any key is waiting, as Windows does.
    """

    def __init__(self, history: Path | None = None, log: Path | None = None) -> None:
        self.history = Path(history) if history is not None else None
        self.log = Path(log) if log is not None else None
        self.proc = ProcId(7, "2026-11-10T14:00:00.0000000Z")
        self.exists = True
        self.foreground = True
        self.responding = True
        self.title = "Victoria 3"
        self.client = (0, 0, 1920, 1080)
        self.idle = 600_000                     # what idle_ms reports
        self.focus_succeeds = True
        self.focus_calls = 0
        self.console_open = False               # Enter runs the typed text while this is set
        self.console_never_opens = False        # the console key does nothing
        self.history_skips_repeats = False      # a command already in the history file is not written to it again
        self.history_encoding = "utf-8"         # what the game writes the history file in (unverified for the real one)
        self.exit_after_steps: int | None = None        # the game ends once this many steps have been sent in all
        self.on_step = None                     # called with the steps sent so far, before each step is tried
        self.latency = 0.0                      # seconds from a key being sent to the game taking it
        self.busy_while_late = False            # the window does not respond while a key is waiting
        self._inbox: list[tuple[float, dict]] = []      # keys sent and not yet taken: (due time, step)
        self.typed = ""                         # text typed since the last Enter
        self.steps: list[dict] = []             # every step sent, as given
        self.now = 0.0
        self.replies: dict[str, tuple[list[str], list[str], list[str]]] = {}
        self.unwritten: list[str] = []          # log lines the game has made but not yet written to the file
        self.launched: list[tuple[str, list, str]] = []
        self.adopted: list[ProcId] = []
        self.killed: list[ProcId] = []
        self.screenshots: list[tuple[int, Path, int]] = []
        self.tcp_port: int | None = None
        self.tcp_in: deque[bytes] = deque()     # what tcp_recv hands out, one chunk a call
        self.tcp_sent: list[bytes] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds
        self._deliver()

    def on(self, text: str, success: Sequence[str] = (), failure: Sequence[str] = (),
           script: Sequence[str] = ()) -> None:
        """What the game answers when `text` is entered: console_success lines, console_failure lines, and
        `debug_log` effect lines from the script it ran (which follow the replies in the log)."""
        self.replies[text] = (list(success), list(failure), list(script))

    def launch(self, exe: str, args: Sequence[str], cwd: str) -> ProcId:
        self.launched.append((exe, list(args), cwd))
        self.exists = True
        return self.proc

    def adopt(self, proc: ProcId) -> None:
        self.adopted.append(proc)

    def window(self, pid: int) -> Window:
        if not self.exists:
            return Window(False, False, False, "", (0, 0, 0, 0))
        responding = self.responding and not (self.busy_while_late and self._inbox)
        return Window(True, self.foreground, responding, self.title, self.client)

    def idle_ms(self) -> int:
        return self.idle

    def focus(self, pid: int) -> bool:
        self.focus_calls += 1
        if self.exists and self.focus_succeeds:
            self.foreground = True
        return self.exists and self.foreground

    def keys(self, pid: int, steps: Sequence[dict]) -> None:
        for step in steps:
            if "\n" in step.get("text", "") or "\r" in step.get("text", ""):
                raise HelperError("bad_text", "typed text must not hold a line break")
        done = 0
        for step in steps:
            if self.on_step is not None:
                self.on_step(len(self.steps))
            if not (self.exists and self.foreground):
                # The real refusal says how far it got, so the caller knows whether a half command is typed.
                raise HelperError("not_foreground", "the game's window is not in front",
                                  reply={"steps_done": done, "chars_sent": 0})
            self.steps.append(dict(step))
            done += 1
            self._inbox.append((self.now + self.latency, dict(step)))
            self._deliver()
            if self.exit_after_steps is not None and len(self.steps) >= self.exit_after_steps:
                self.exists = False

    def _deliver(self) -> None:
        """The game takes the keys that are due, in the order they were sent."""
        while self._inbox and self._inbox[0][0] <= self.now:
            _due, step = self._inbox.pop(0)
            if "text" in step:
                self.typed += step["text"]
            elif step.get("scan") == SCAN_ENTER:
                self._enter()
            elif step.get("scan") == SCAN_CONSOLE and not self.console_never_opens:
                self.console_open = not self.console_open
            elif step.get("scan") == SCAN_BACKSPACE:
                self.typed = self.typed[:-1]

    def _enter(self) -> None:
        text, self.typed = self.typed, ""
        if not (self.console_open and text):
            return
        if self.history is not None:
            self.history.parent.mkdir(parents=True, exist_ok=True)
            known = self.history.read_text(encoding=self.history_encoding).split("\n") if self.history.exists() else []
            if not (self.history_skips_repeats and text in known):
                with open(self.history, "a", encoding=self.history_encoding) as f:
                    f.write(text + "\n")
        self._run(text)

    def _logged(self, source: str, message: str) -> None:
        clock = int(self.now)
        self.unwritten.append("[%02d:%02d:%02d][%s]: %s" % (12 + clock // 3600 % 12, clock // 60 % 60, clock % 60,
                                                          source, message))

    def _run(self, text: str) -> None:
        """The game runs a command: its lines go to the buffer, and a flush writes the buffer out."""
        success, failure, script = self.replies.get(text, ([], [], []))
        self._logged("console.cpp:1175", "Running console command: " + text)
        for line in success:
            self._logged("console.cpp:1203", "console_success: " + line)
        for line in failure:
            self._logged("console.cpp:1203", "console_failure: " + line)
        for line in script:
            self._logged("jomini_effect_impl.cpp:459", line)
        if text != FLUSH_COMMAND:
            return
        for n in range(_HELP_LINES):
            self._logged("console.cpp:1203", "console_success: ndefines.ngui option %d" % n)
        out, self.unwritten = self.unwritten[:-_HELD_BACK], self.unwritten[-_HELD_BACK:]
        if self.log is not None:
            with open(self.log, "a", encoding="utf-8", newline="\n") as f:
                f.write("".join(line + "\n" for line in out))

    def screenshot(self, pid: int, path: Path, max_width: int = 1600) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(win_helper.encode_png(1, 1, b"\x00\x00\x00"))
        self.screenshots.append((pid, path, max_width))
        return path

    def kill(self, proc: ProcId) -> None:
        self.killed.append(proc)
        self.exists = False

    def tcp_open(self, port: int) -> None:
        self.tcp_port = port

    def tcp_send(self, data: bytes) -> None:
        self.tcp_sent.append(bytes(data))

    def tcp_recv(self, timeout: float) -> bytes:
        return self.tcp_in.popleft() if self.tcp_in else b""

    def tcp_close(self) -> None:
        self.tcp_port = None
