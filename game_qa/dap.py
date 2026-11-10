"""A small Debug Adapter Protocol client for the game's script debugger.

Victoria 3 1.15 opens a debug-adapter socket on 127.0.0.1:6111 when started
with `-script_debugger` (spec § 3.5). Stopped at a breakpoint on a line of a
mod file, it evaluates triggers and dotted values in that line's scope, which
is how the harness reads game state without a reload or a log flush.

The client takes `send(bytes)` and `recv(timeout_seconds) -> bytes` (empty on
timeout), so it runs over the Windows helper's TCP relay and over a fake in
tests.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Callable

_HEADER_END = b"\r\n\r\n"
_LENGTH = re.compile(rb"Content-Length: *(\d+)", re.IGNORECASE)
_YES_NO = re.compile(r"^(yes|no)\b", re.IGNORECASE)
GAME_THREAD = 1


def encode(msg: dict) -> bytes:
    body = json.dumps(msg, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


class Decoder:
    """Feed it bytes as they arrive; it returns the whole messages so far and
    keeps a partial one for the next call."""

    def __init__(self) -> None:
        self._buf = b""

    def feed(self, data: bytes) -> list[dict]:
        self._buf += data
        out = []
        while True:
            end = self._buf.find(_HEADER_END)
            if end < 0:
                return out
            m = _LENGTH.search(self._buf[:end])
            if not m:
                raise DebuggerError("message without a Content-Length header")
            start = end + len(_HEADER_END)
            length = int(m.group(1))
            if len(self._buf) < start + length:
                return out
            out.append(json.loads(self._buf[start:start + length].decode("utf-8")))
            self._buf = self._buf[start + length:]


class DebuggerError(Exception):
    pass


@dataclass
class Eval:
    ok: bool
    raw: str
    value: bool | float | None


def _value_of(raw: str) -> bool | float | None:
    text = raw.strip()
    m = _YES_NO.match(text)
    if m:
        return m.group(1).lower() == "yes"
    try:
        return float(text)
    except ValueError:
        return None


class Debugger:
    def __init__(self, send: Callable[[bytes], None], recv: Callable[[float], bytes]):
        self._send = send
        self._recv = recv
        self._decoder = Decoder()
        self._seq = 0
        self._replies: dict[int, dict] = {}
        self._errors: list[str] = []
        self._stops = 0

    # -- plumbing -----------------------------------------------------------

    def _pump(self, timeout: float) -> None:
        """Read once and file what arrived: replies by request, error-log
        output, stops."""
        for msg in self._decoder.feed(self._recv(timeout)):
            kind = msg.get("type")
            if kind == "response":
                self._replies[msg.get("request_seq")] = msg
            elif kind == "event":
                event, body = msg.get("event"), msg.get("body") or {}
                if event == "output" and body.get("category") == "stderr":
                    self._errors.append(str(body.get("output", "")).rstrip("\n"))
                elif event == "stopped":
                    self._stops += 1

    def _request(self, command: str, arguments: dict | None = None, timeout: float = 30.0) -> dict:
        """Send one request and wait for its own reply; events and other
        replies that arrive first (hundreds, after an evaluation) are filed."""
        self._seq += 1
        seq = self._seq
        msg: dict = {"seq": seq, "type": "request", "command": command}
        if arguments is not None:
            msg["arguments"] = arguments
        self._send(encode(msg))
        deadline = time.monotonic() + timeout
        while seq not in self._replies:
            left = deadline - time.monotonic()
            if left <= 0:
                raise DebuggerError(f"no reply to {command!r} within {timeout} s")
            self._pump(min(left, 0.5))
        return self._replies.pop(seq)

    def _must(self, command: str, arguments: dict | None = None, timeout: float = 30.0) -> dict:
        reply = self._request(command, arguments, timeout)
        if not reply.get("success"):
            raise DebuggerError(f"{command} refused: {reply.get('message', '')}")
        return reply.get("body") or {}

    # -- the session --------------------------------------------------------

    def attach(self, breakpoints: dict[str, list[int]] | None = None) -> dict[str, list[bool]]:
        """`initialize`, `launch`, one `setBreakpoints` per file, then
        `configurationDone`: the order the probe used. Returns each
        breakpoint's `verified` flag, by file."""
        self._must("initialize", {"clientID": "game_qa", "adapterID": "jomini",
                                  "linesStartAt1": True, "columnsStartAt1": True})
        self._must("launch", {})
        verified: dict[str, list[bool]] = {}
        for path, lines in (breakpoints or {}).items():
            body = self._must("setBreakpoints", {"source": {"path": path},
                                                 "breakpoints": [{"line": n} for n in lines]})
            verified[path] = [bool(b.get("verified")) for b in body.get("breakpoints", [])]
        self._must("configurationDone")
        return verified

    def wait_stopped(self, timeout: float) -> bool:
        """True once per stop at a breakpoint."""
        deadline = time.monotonic() + timeout
        while not self._stops:
            left = deadline - time.monotonic()
            if left <= 0:
                return False
            self._pump(min(left, 0.5))
        self._stops -= 1
        return True

    def evaluate(self, expr: str, frame: int = 0, timeout: float = 30.0) -> Eval:
        """A trigger (`is_player = yes`) or a dotted value (`c:FRA.gdp`) in the
        stopped frame's scope. The game refuses unless it is stopped."""
        reply = self._request("evaluate", {"expression": expr, "frameId": frame, "context": "watch"}, timeout)
        if not reply.get("success"):
            return Eval(False, str(reply.get("message", "")), None)
        raw = str((reply.get("body") or {}).get("result", ""))
        return Eval(True, raw, _value_of(raw))

    def scopes(self, frame: int = 0) -> dict[str, dict[str, str]]:
        """`{"Scope": {"this": …, "root": …, "prev": …}, "Saved Scopes": {…}}`."""
        out: dict[str, dict[str, str]] = {}
        for scope in self._must("scopes", {"frameId": frame}).get("scopes", []):
            ref = scope.get("variablesReference")
            variables = self._must("variables", {"variablesReference": ref}).get("variables", []) if ref else []
            out[str(scope.get("name"))] = {str(v.get("name")): str(v.get("value")) for v in variables}
        return out

    def resume(self) -> None:
        self._must("continue", {"threadId": GAME_THREAD})

    def errors(self) -> list[str]:
        """The error-log lines the game has streamed since the last call."""
        drained, self._errors = self._errors, []
        return drained
