"""The WSL side of the Windows helper: the `Helper` protocol and `ProcessHelper`.

`ProcessHelper` starts `game_qa/win_helper.py` under the Windows python.exe and
speaks JSON lines to it over pipes (one request line, one reply line). Every
other module takes a `Helper`, so tests give them `fakes.FakeHelper` instead.
"""
from __future__ import annotations

import base64
import json
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from game_qa.gate import ProcId


class HelperError(Exception):
    """A refusal or failure from the helper. `code` is the reply's `error`; `reply` is the whole reply."""

    def __init__(self, code: str, detail: str = "", reply: dict | None = None) -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail, self.reply = code, detail, reply or {}


@dataclass
class Window:
    exists: bool
    foreground: bool
    responding: bool
    title: str
    client: tuple[int, int, int, int]       # x, y, width, height of the client area, in screen pixels


@dataclass(frozen=True)
class Presence:
    """Where the cursor and the foreground window were at one reading, and where the helper last put the cursor.

    Two readings that differ in the foreground window, or in a cursor that is not at `helper_cursor`, mean a person
    was at the machine between them. Coordinates are screen pixels; `foreground` is a window handle (0: none)."""
    cursor: tuple[int, int]
    foreground: int
    helper_cursor: tuple[int, int] | None


class Helper(Protocol):
    def launch(self, exe: str, args: Sequence[str], cwd: str) -> ProcId: ...
    def adopt(self, proc: ProcId) -> None: ...
    def window(self, pid: int) -> Window: ...
    def idle_ms(self) -> int: ...
    def focus(self, pid: int) -> bool: ...
    def keys(self, pid: int, steps: Sequence[dict]) -> None: ...
    def click(self, pid: int, x: int, y: int) -> None: ...
    # click: x, y in client pixels. Refused (HelperError) with not_foreground, bad_point (outside the client area, or
    # the window moved), cursor_misplaced or covered, in which cases nothing was pressed.
    def presence(self) -> Presence: ...
    def screenshot(self, pid: int, path: Path, max_width: int = 1600) -> Path: ...
    def kill(self, proc: ProcId) -> bool: ...      # True if the process had already exited
    def tcp_open(self, port: int) -> None: ...
    def tcp_send(self, data: bytes) -> None: ...
    def tcp_recv(self, timeout: float) -> bytes: ...
    def tcp_close(self) -> None: ...


def to_windows_path(path: Path, run=subprocess.run) -> str:
    """`path` as Windows names it (`wslpath -w`): a drive path under /mnt, else a \\\\wsl.localhost\\ one."""
    done = run(["wslpath", "-w", str(path)], capture_output=True, text=True, check=True)
    return done.stdout.rstrip("\r\n")


class ProcessHelper:
    """Runs win_helper.py under the Windows Python and talks to it; starts it on the first call.

    Once the helper's pipe closes, every call raises `HelperError("helper_gone")`:
    a new helper would not remember which processes it started.
    """

    def __init__(self, python_exe: str = "python.exe", popen=subprocess.Popen, run=subprocess.run,
                 script: Path | None = None) -> None:
        self._python_exe, self._popen, self._run = python_exe, popen, run
        self._script = Path(script) if script is not None else Path(__file__).resolve().with_name("win_helper.py")
        self._proc = None
        self._gone = False
        self._next_id = 0
        self._lock = threading.Lock()

    def _start(self) -> None:
        try:
            argv = [self._python_exe, "-u", to_windows_path(self._script, run=self._run)]
            # Binary pipes: Windows Python's text pipes are cp1252 with CRLF. Its stderr is left alone,
            # so a crash on start-up shows in our own.
            self._proc = self._popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        except (OSError, subprocess.SubprocessError) as e:
            self._gone = True
            raise HelperError("helper_gone", "could not start %s: %r" % (self._python_exe, e)) from e

    def _call(self, op: str, **fields) -> dict:
        with self._lock:
            if self._gone:
                raise HelperError("helper_gone", "the helper has ended")
            if self._proc is None:
                self._start()
            self._next_id += 1
            line = (json.dumps({"id": self._next_id, "op": op, **fields}) + "\n").encode("ascii")
            try:
                self._proc.stdin.write(line)
                self._proc.stdin.flush()
                raw = self._proc.stdout.readline()
            except (OSError, ValueError) as e:      # a broken pipe, or I/O on a closed one
                self._gone = True
                raise HelperError("helper_gone", repr(e)) from e
            if not raw:
                self._gone = True
                raise HelperError("helper_gone", "the helper's output closed")
        try:
            reply = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        except ValueError:
            reply = None
        if not isinstance(reply, dict):
            raise HelperError("bad_reply", repr(raw[:200]))
        if not reply.get("ok"):
            raise HelperError(str(reply.get("error", "unknown")), str(reply.get("detail", "")), reply)
        return reply

    def close(self) -> None:
        """End the helper (not the game): closing its input makes it exit."""
        with self._lock:
            proc, self._proc, self._gone = self._proc, None, True
        if proc is None:
            return
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    def ping(self) -> str:
        """The helper's Python version."""
        return self._call("ping")["python"]

    def launch(self, exe: str, args: Sequence[str], cwd: str) -> ProcId:
        reply = self._call("launch", exe=exe, args=list(args), cwd=cwd)
        return ProcId(int(reply["pid"]), str(reply["created"]))

    def adopt(self, proc: ProcId) -> None:
        self._call("adopt", pid=proc.pid, created=proc.created)

    def window(self, pid: int) -> Window:
        r = self._call("window", pid=pid)
        return Window(bool(r["exists"]), bool(r["foreground"]), bool(r["responding"]), str(r["title"]),
                      tuple(int(v) for v in r["client"]))

    def idle_ms(self) -> int:
        return int(self._call("idle_ms")["idle_ms"])

    def focus(self, pid: int) -> bool:
        return bool(self._call("focus", pid=pid)["foreground"])

    def keys(self, pid: int, steps: Sequence[dict]) -> None:
        self._call("keys", pid=pid, steps=list(steps))

    def click(self, pid: int, x: int, y: int) -> None:
        self._call("click", pid=pid, x=x, y=y)

    def presence(self) -> Presence:
        r = self._call("presence")
        mine = r.get("helper_cursor")
        return Presence((int(r["cursor"][0]), int(r["cursor"][1])), int(r["foreground"]),
                        None if mine is None else (int(mine[0]), int(mine[1])))

    def screenshot(self, pid: int, path: Path, max_width: int = 1600) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # wslpath can fail on a file that does not exist yet, so convert the folder and add the name.
        folder = to_windows_path(path.parent, run=self._run)
        self._call("screenshot", pid=pid, path=folder.rstrip("\\") + "\\" + path.name, max_width=max_width)
        return path

    def kill(self, proc: ProcId) -> bool:
        """End a process this helper started. True if it had already exited (there was nothing to end)."""
        return bool(self._call("kill", pid=proc.pid).get("already_exited", False))

    def tcp_open(self, port: int) -> None:
        self._call("tcp_open", port=port)

    def tcp_send(self, data: bytes) -> None:
        self._call("tcp_send", b64=base64.b64encode(data).decode("ascii"))

    def tcp_recv(self, timeout: float) -> bytes:
        return base64.b64decode(self._call("tcp_recv", timeout_ms=int(timeout * 1000))["b64"])

    def tcp_close(self) -> None:
        self._call("tcp_close")
