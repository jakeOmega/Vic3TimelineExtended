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
    """

    def __init__(self, history: Path | None = None) -> None:
        self.history = Path(history) if history is not None else None
        self.proc = ProcId(7, "2026-11-10T14:00:00.0000000Z")
        self.exists = True
        self.foreground = True
        self.responding = True
        self.title = "Victoria 3"
        self.client = (0, 0, 1920, 1080)
        self.idle = 600_000                     # what idle_ms reports
        self.focus_succeeds = True
        self.focus_calls = 0
        self.console_open = False               # Enter appends the typed text to the history while this is set
        self.typed = ""                         # text typed since the last Enter
        self.steps: list[dict] = []             # every step sent, as given
        self.launched: list[tuple[str, list, str]] = []
        self.adopted: list[ProcId] = []
        self.killed: list[ProcId] = []
        self.screenshots: list[tuple[int, Path, int]] = []
        self.tcp_port: int | None = None
        self.tcp_in: deque[bytes] = deque()     # what tcp_recv hands out, one chunk a call
        self.tcp_sent: list[bytes] = []

    def launch(self, exe: str, args: Sequence[str], cwd: str) -> ProcId:
        self.launched.append((exe, list(args), cwd))
        self.exists = True
        return self.proc

    def adopt(self, proc: ProcId) -> None:
        self.adopted.append(proc)

    def window(self, pid: int) -> Window:
        if not self.exists:
            return Window(False, False, False, "", (0, 0, 0, 0))
        return Window(True, self.foreground, self.responding, self.title, self.client)

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
        for step in steps:
            if not (self.exists and self.foreground):
                raise HelperError("not_foreground", "the game's window is not in front")
            self.steps.append(dict(step))
            if "text" in step:
                self.typed += step["text"]
            elif step.get("scan") == SCAN_ENTER:
                self._enter()

    def _enter(self) -> None:
        if self.console_open and self.typed and self.history is not None:
            self.history.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history, "a", encoding="utf-8") as f:
                f.write(self.typed + "\n")
        self.typed = ""

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
