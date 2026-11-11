"""A small Debug Adapter Protocol client for the game's script debugger.

Victoria 3 1.15 opens a debug-adapter socket on 127.0.0.1:6111 when started
with `-script_debugger` (spec § 3.5). Stopped at a breakpoint on a line of a
mod file, it evaluates triggers and dotted values in that line's scope, which
is how the harness reads game state without a reload or a log flush.

The client takes `send(bytes)` and `recv(timeout_seconds) -> bytes` (empty on
timeout), so it runs over the Windows helper's TCP relay and over a fake in
tests. Either callable may raise (the relay does when the connection ends):
the client turns that into a `DebuggerError` that keeps the original as its
`__cause__`.
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
    keeps a partial one for the next call.

    One bad message never costs the others: a message is taken out of the
    buffer before it is read, a body that is not UTF-8 is read with replacement
    characters, and a body that is not a JSON object, or a header block with no
    `Content-Length`, is dropped. `skipped` counts what was dropped."""

    def __init__(self) -> None:
        self._buf = b""
        self.skipped = 0

    def feed(self, data: bytes) -> list[dict]:
        self._buf += data
        out = []
        while True:
            end = self._buf.find(_HEADER_END)
            if end < 0:
                return out
            m = _LENGTH.search(self._buf[:end])
            start = end + len(_HEADER_END)
            if not m:
                self._buf = self._buf[start:]       # not a message: drop the block, go on with what follows
                self.skipped += 1
                continue
            length = int(m.group(1))
            if len(self._buf) < start + length:
                return out
            body, self._buf = self._buf[start:start + length], self._buf[start + length:]
            try:
                msg = json.loads(body.decode("utf-8", errors="replace"))
            except ValueError:
                msg = None
            if isinstance(msg, dict):
                out.append(msg)
            else:
                self.skipped += 1


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
        self._reasons: list[str | None] = []        # each stop not yet taken: its `reason`, in order
        self._forget_stops_at: int | None = None    # seq of a request whose answer ends the stops seen so far
        self.last_stop_reason: str | None = None    # the reason of the stop `wait_stopped` last took, if it gave one

    @property
    def skipped(self) -> int:
        """How many messages the client dropped as not being messages (see `Decoder`) or having a shape it
        cannot file."""
        return self._decoder.skipped

    # -- plumbing -----------------------------------------------------------

    @staticmethod
    def _through(fn: Callable, what: str, *args):
        """Call the transport; whatever it raises is a `DebuggerError` (the original is its `__cause__`)."""
        try:
            return fn(*args)
        except Exception as e:
            raise DebuggerError(f"{what} failed: {e!r}") from e

    def _pump(self, timeout: float) -> None:
        """Read once and file what arrived: replies by request, error-log
        output, stops. A message of a shape that cannot be filed (a body that
        is not an object, a `request_seq` that is not a number) is counted in
        `skipped`, like one that is not a message, and the rest of what
        arrived is still filed."""
        for msg in self._decoder.feed(self._through(self._recv, "recv", timeout)):
            body = msg.get("body")
            if body and not isinstance(body, dict):
                self._decoder.skipped += 1
                continue
            kind = msg.get("type")
            if kind == "response":
                seq = msg.get("request_seq")
                if not isinstance(seq, int):
                    self._decoder.skipped += 1
                    continue
                self._replies[seq] = msg
                if seq == self._forget_stops_at:
                    # Everything seen before this answer is from before the game ran on; what follows it in the
                    # same read (`continued`, a `stopped` at a breakpoint it passes again at once) is new.
                    self._forget_stops_at = None
                    self._forget_stops()
            elif kind == "event":
                event, body = msg.get("event"), body or {}
                if event == "output" and body.get("category") == "stderr":
                    self._errors.append(str(body.get("output", "")).rstrip("\n"))
                elif event == "stopped":
                    self._stops += 1
                    reason = body.get("reason")
                    self._reasons.append(reason if isinstance(reason, str) else None)

    def _forget_stops(self) -> None:
        self._stops = 0
        self._reasons.clear()
        self.last_stop_reason = None

    def _request(self, command: str, arguments: dict | None = None, timeout: float = 30.0,
                 forgets_stops: bool = False) -> dict:
        """Send one request and wait for its own reply; events and other
        replies that arrive first (hundreds, after an evaluation) are filed.
        With `forgets_stops`, the stops counted when its reply is filed are
        dropped (`_pump` does it at that moment)."""
        self._seq += 1
        seq = self._seq
        msg: dict = {"seq": seq, "type": "request", "command": command}
        if arguments is not None:
            msg["arguments"] = arguments
        if forgets_stops:
            self._forget_stops_at = seq
        self._through(self._send, "send", encode(msg))
        deadline = time.monotonic() + timeout
        while seq not in self._replies:
            left = deadline - time.monotonic()
            if left <= 0:
                raise DebuggerError(f"no reply to {command!r} within {timeout} s")
            self._pump(min(left, 0.5))
        return self._replies.pop(seq)

    def _must(self, command: str, arguments: dict | None = None, timeout: float = 30.0,
              forgets_stops: bool = False) -> dict:
        reply = self._request(command, arguments, timeout, forgets_stops)
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
        """True once per `stopped` event the game has sent, whatever its reason (a breakpoint, a step, a
        pause), within `timeout` seconds; `last_stop_reason` is then that stop's reason. `resume()` forgets the
        stops not yet taken, and the reason with them."""
        deadline = time.monotonic() + timeout
        while not self._stops:
            left = deadline - time.monotonic()
            if left <= 0:
                return False
            self._pump(min(left, 0.5))
        return self._take_stop()

    def poll_stopped(self) -> bool:
        """`wait_stopped` without the wait: one look at what has arrived (`recv(0)`, which the helper turns into
        a 1 ms poll), then True once per stop not yet taken. `wait_stopped(0)` would not look at all."""
        if not self._stops:
            self._pump(0)
        return self._take_stop() if self._stops else False

    def _take_stop(self) -> bool:
        self._stops -= 1
        self.last_stop_reason = self._reasons.pop(0) if self._reasons else None
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
        """Let the game run on. Every stop counted up to the moment the game's answer is filed is the old one,
        not the next: it is forgotten, so it cannot satisfy the next `wait_stopped`, whether the game accepts
        the request or not. A `stopped` that comes after the answer, even in the same read of the connection
        (the order seen live: the answer, `continued`, `stopped`), is the next one and counts. If no answer is
        ever filed (the connection fails, or the game does not answer in time) the old stops are forgotten
        when the error is raised."""
        try:
            self._must("continue", {"threadId": GAME_THREAD}, forgets_stops=True)
        finally:
            if self._forget_stops_at is not None:       # no answer was filed
                self._forget_stops_at = None
                self._forget_stops()

    def errors(self) -> list[str]:
        """The error-log lines the game has streamed since the last call."""
        drained, self._errors = self._errors, []
        return drained
