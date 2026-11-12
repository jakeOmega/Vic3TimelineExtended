"""The Windows side of the in-game QA harness (spec § 5.1).

One self-contained file, run by the Windows python.exe (3.11) from a
\\\\wsl.localhost\\ path and spoken to in JSON lines: a request on standard
input, one reply line on standard output. It imports nothing from the
`game_qa` package, and nothing here touches a Windows-only module until
`make_backend()` builds `WindowsBackend` on Windows, so the file also imports
on Linux, where the tests drive `handle` with `fakes.FakeBackend`.

A request is `{"id": n, "op": "<name>", ...}`; a reply is
`{"id": n, "ok": true, ...}` or `{"id": n, "ok": false, "error": "<code>"}`.
`handle` never raises.

What the helper refuses, because a wrong key in the owner's session is worse
than a failed step:

  * keys go only to the process's own window while that window is in front,
    checked again before every step and before every character of typed text;
  * keys, a click and the ALT tap of `focus` go only to a process this helper
    started or adopted, and only while the live process still has the creation
    time recorded then, read again before every step, every character and the
    press (`not_ours`): a batch that began at the game must not end at whatever
    program took its id when the game died;
  * a process is ended only if this helper started it (or was told its
    creation time) and the live process still has that creation time: a
    process id is reused, the pair is not. One it started that has already
    exited is answered `ok` with `already_exited`, and forgotten;
  * the TCP relay connects to 127.0.0.1 and nowhere else.

`idle_ms` is the time since the latest keyboard or mouse input that the helper
did not send itself: the system reports the latest input of any kind, so the
helper remembers when it sent its own and discounts input at that moment.
(Over a remote-desktop session it reads 0 to 31 ms continuously, which is why
the console decides whether someone is at the machine from `presence` instead.)

`click` moves the cursor to a point of the game's client area and presses the
left button there, under the same rule as `keys` (the game's window in front),
and presses only if, after the cursor has settled, the window is still in front
and has not moved, the cursor is exactly on the point, and the game's own window
is the one under it. Otherwise nothing is pressed: `not_foreground`, `bad_point`,
`cursor_misplaced` or `covered`. `presence`
reports where the cursor and the foreground window are, and where the helper
last put the cursor, so that a caller comparing two readings can tell its
own move from a person's.
"""
from __future__ import annotations

import base64
import binascii
import ctypes
import json
import operator
import os
import platform
import socket
import struct
import subprocess
import sys
import time
import zlib
from datetime import datetime, timedelta, timezone

LOOPBACK = "127.0.0.1"
ALLOWANCE_MS = 50           # input this soon after our own key-up is still ours
DEFAULT_MAX_WIDTH = 1600
DEFAULT_RECV_TIMEOUT_MS = 1000
RECV_BYTES = 65536
SEND_TIMEOUT_S = 5.0          # a send never inherits the 1 ms a poll-style tcp_recv left on the socket
TEXT_CHUNK_CHARS = 1          # typed text goes out this many characters at a time, the foreground checked before each:
                              # one, so a window that takes the front mid-text gets at most the character on its way
KEY_HOLD_S = 0.04             # between key down and key up; the game ignores a shorter press
CHAR_GAP_S = 0.008
CLICK_SETTLE_MS = 120         # from the cursor moving to the button going down, as in the probe: the game's hover catches up
CLICK_HOLD_MS = 60            # between the button going down and up

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_LEFTDOWN = 0x0002     # not the keyboard flags below, whose values these share
MOUSEEVENTF_LEFTUP = 0x0004
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

_FILETIME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


# --- Win32 structures, in fixed-width types so their layout can be checked on
# --- any platform (wintypes.DWORD and c_long are 8 bytes on Linux).

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_int32), ("top", ctypes.c_int32),
                ("right", ctypes.c_int32), ("bottom", ctypes.c_int32)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int32), ("y", ctypes.c_int32)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_int32), ("dy", ctypes.c_int32), ("mouseData", ctypes.c_uint32),
                ("dwFlags", ctypes.c_uint32), ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_uint16), ("wScan", ctypes.c_uint16), ("dwFlags", ctypes.c_uint32),
                ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_uint32), ("wParamL", ctypes.c_uint16), ("wParamH", ctypes.c_uint16)]


class _INPUTUNION(ctypes.Union):
    # The union is as large as its largest member, MOUSEINPUT: that is what
    # makes sizeof(INPUT) 40 on 64-bit Windows, and SendInput rejects any other size.
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_uint32), ("u", _INPUTUNION)]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("dwTime", ctypes.c_uint32)]


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32), ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32), ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32), ("biClrImportant", ctypes.c_uint32)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 1)]


# --- Pure functions (tested on Linux).

def filetime_to_iso(ticks: int) -> str:
    """A FILETIME (100 ns since 1601-01-01 UTC) as PowerShell's ToString('o') writes a UTC DateTime.

    The WSL side compares these strings for equality with the ones PowerShell
    printed, so the shape is fixed: seven fractional digits and a trailing Z.
    """
    seconds, fraction = divmod(ticks, 10_000_000)
    moment = _FILETIME_EPOCH + timedelta(seconds=seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + ".%07dZ" % fraction


def utf16_units(text: str) -> list[int]:
    """The 16-bit code units SendInput types for `text`: a character outside the BMP is two."""
    data = text.encode("utf-16-le", "surrogatepass")
    return list(struct.unpack("<%dH" % (len(data) // 2), data))


def scale_rgb(width: int, height: int, rgb: bytes, max_width: int) -> tuple[int, int, bytes]:
    """`rgb` (3 bytes a pixel, top row first) scaled down, nearest neighbour, to at most `max_width` wide."""
    stride = width * 3
    if width < 1 or height < 1 or len(rgb) != stride * height:
        raise ValueError("%d bytes is not a %dx%d RGB image" % (len(rgb), width, height))
    if max_width < 1:
        raise ValueError("max_width must be at least 1")
    if width <= max_width:
        return width, height, rgb
    new_w = max_width
    new_h = max(1, height * new_w // width)
    columns = [((2 * x + 1) * width) // (2 * new_w) for x in range(new_w)]
    pick = operator.itemgetter(*[c * 3 + k for c in columns for k in range(3)])
    out = bytearray()
    for y in range(new_h):
        sy = ((2 * y + 1) * height) // (2 * new_h)
        out += bytes(pick(rgb[sy * stride:(sy + 1) * stride]))
    return new_w, new_h, bytes(out)


def encode_png(width: int, height: int, rgb: bytes) -> bytes:
    """A PNG (8-bit RGB, no filtering, no interlace) of `rgb`, from zlib and struct alone."""
    stride = width * 3
    if width < 1 or height < 1 or len(rgb) != stride * height:
        raise ValueError("%d bytes is not a %dx%d RGB image" % (len(rgb), width, height))
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))


def bgra_to_rgb(width: int, height: int, bgra: bytes) -> bytes:
    """A 32-bit-per-pixel BGRA capture (what GetDIBits returns) as 3-byte RGB, same row order."""
    if width < 1 or height < 1 or len(bgra) != width * height * 4:
        raise ValueError("%d bytes is not a %dx%d BGRA image" % (len(bgra), width, height))
    rgb = bytearray(width * height * 3)
    rgb[0::3] = bgra[2::4]
    rgb[1::3] = bgra[1::4]
    rgb[2::3] = bgra[0::4]
    return bytes(rgb)


def tick_age_ms(now32: int, then32: int) -> int:
    """Milliseconds from `then32` to `now32`, both 32-bit tick counts that wrap every 49.7 days."""
    return (now32 - then32) & 0xFFFFFFFF


def last_input_tick_from(tick64: int, now32: int, input32: int) -> int:
    """When the last input was, on the 64-bit tick clock: GetLastInputInfo only has the 32-bit one."""
    return tick64 - tick_age_ms(now32, input32)


def text_chunks(text: str, size: int = TEXT_CHUNK_CHARS) -> list[str]:
    """`text` in pieces of at most `size` characters (never splitting a character); an empty text is one empty piece."""
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def tap_key(send, sleep, code: int, flags: int, hold_s: float) -> None:
    """Press then release one key through `send(code, flags)`. Once the press went out, the release is
    always attempted, even if the wait between them fails: a key left held types into whatever is in front."""
    send(code, flags)
    try:
        sleep(hold_s)
    finally:
        send(code, flags | KEYEVENTF_KEYUP)


def tap_button(send, sleep, hold_ms: int) -> None:
    """Press then release the left mouse button through `send(flags)`. The release is always attempted once the
    press has begun, even if the press or the wait after it fails: a button left held drags whatever is under it."""
    try:
        send(MOUSEEVENTF_LEFTDOWN)
        sleep(hold_ms)
    finally:
        send(MOUSEEVENTF_LEFTUP)


# --- The request handler.

class State:
    """What the helper remembers between requests."""

    def __init__(self) -> None:
        self.ours: dict[int, str] = {}              # pid -> creation time, for the processes it may end
        self.last_sent_tick: int | None = None      # tick at which it last sent a key (None: never)
        self.last_foreign_tick: int | None = None   # tick of the latest input it did not send
        self.helper_cursor: tuple[int, int] | None = None     # where its last click left the cursor, in screen pixels
        self.sock = None                            # the TCP relay's connection, if open


class _Refusal(Exception):
    def __init__(self, code: str, detail: str = "", **fields) -> None:
        super().__init__(code)
        self.code, self.detail, self.fields = code, detail, fields


_MISSING = object()


def _int(req: dict, name: str, low: int | None = None, high: int | None = None, default=_MISSING) -> int:
    value = req.get(name, default)
    if value is _MISSING:
        raise _Refusal("bad_request", "%s is missing" % name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _Refusal("bad_request", "%s must be an integer" % name)
    if (low is not None and value < low) or (high is not None and value > high):
        raise _Refusal("bad_request", "%s is out of range" % name)
    return value


def _str(req: dict, name: str, empty: bool = True, default=_MISSING) -> str:
    value = req.get(name, default)
    if value is _MISSING:
        raise _Refusal("bad_request", "%s is missing" % name)
    if not isinstance(value, str) or (not empty and not value):
        raise _Refusal("bad_request", "%s must be %s string" % (name, "a" if empty else "a non-empty"))
    return value


def _pid(req: dict) -> int:
    return _int(req, "pid", low=1)


def _observe(backend, state: State) -> None:
    """Look at the system's latest input; if the helper did not send it, a person did."""
    seen = backend.last_input_tick()
    if (state.last_sent_tick is None or state.last_foreign_tick is None
            or seen > state.last_sent_tick + ALLOWANCE_MS):
        state.last_foreign_tick = seen


def _window(backend, pid: int) -> dict | None:
    win = backend.window_of(pid)
    return win if win and win["hwnd"] else None


def _in_front(backend, pid: int) -> bool:
    win = _window(backend, pid)
    return win is not None and backend.foreground_hwnd() == win["hwnd"]


def _close_socket(state: State) -> None:
    sock, state.sock = state.sock, None
    if sock is not None:
        try:
            sock.close()
        except OSError:
            pass


def _open_socket(state: State):
    if state.sock is None:
        raise _Refusal("not_open", "no TCP connection is open")
    return state.sock


def _op_ping(req, backend, state):
    return {"python": platform.python_version()}


def _op_launch(req, backend, state):
    exe = _str(req, "exe", empty=False)
    args = req.get("args", [])
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise _Refusal("bad_request", "args must be a list of strings")
    cwd = _str(req, "cwd", default="")
    pid = backend.create_process(exe, args, cwd)
    created = backend.creation_time(pid)
    if created is None:
        raise _Refusal("launch_failed", "the process was gone before its creation time could be read")
    state.ours[pid] = created
    return {"pid": pid, "created": created}


def _op_adopt(req, backend, state):
    pid, created = _pid(req), _str(req, "created", empty=False)
    if backend.creation_time(pid) != created:
        raise _Refusal("not_ours", "no live process %d was created at %s" % (pid, created))
    state.ours[pid] = created
    return {}


def _op_window(req, backend, state):
    pid = _pid(req)
    win = _window(backend, pid)
    if win is None:
        return {"exists": False, "hwnd": 0, "title": "", "foreground": False, "responding": False,
                "client": [0, 0, 0, 0]}
    return {"exists": True, "hwnd": win["hwnd"], "title": win["title"],
            "foreground": backend.foreground_hwnd() == win["hwnd"],
            "responding": bool(win["responding"]), "client": list(win["client"])}


def _op_idle_ms(req, backend, state):
    _observe(backend, state)
    return {"idle_ms": max(0, backend.tick() - state.last_foreign_tick)}


def _prove_ours(backend, state: State, pid: int, **fields) -> None:
    """The process is still the one this helper started or adopted: its creation time is read again and compared
    with the one recorded then, as `_op_adopt` and `_op_kill` compare it (an id is reused, the pair is not). A
    process never recorded is refused the same way, so no input goes out by a process id alone."""
    recorded = state.ours.get(pid)
    if recorded is None:
        raise _Refusal("not_ours", "process %d was not started or adopted by this helper" % pid, **fields)
    if backend.creation_time(pid) != recorded:
        raise _Refusal("not_ours", "no live process %d was created at %s" % (pid, recorded), **fields)


def _op_focus(req, backend, state):
    pid = _pid(req)
    win = _window(backend, pid)
    _prove_ours(backend, state, pid)    # after the lookup by id, so it vouches for the window found; before any tap
    if win is None:
        return {"foreground": False}
    _observe(backend, state)            # before our own ALT tap lands in the system's input time
    if backend.foreground_hwnd() != win["hwnd"]:
        _front, tapped_at = backend.set_foreground(win["hwnd"])
        if tapped_at is not None:       # only a tap that was sent is our input, and only from the moment it went out
            state.last_sent_tick = tapped_at
    return {"foreground": _in_front(backend, pid)}


def _steps(req: dict) -> list[tuple[str, object]]:
    """Every step checked before the first is sent: a malformed one, or a line break in typed text, sends nothing."""
    steps = req.get("steps")
    if not isinstance(steps, list):
        raise _Refusal("bad_request", "steps must be a list")
    checked: list[tuple[str, object]] = []
    for step in steps:
        if not isinstance(step, dict) or len(step) != 1:
            raise _Refusal("bad_request", "a step is an object with one of scan, text or wait_ms")
        ((kind, value),) = step.items()
        if kind == "scan":
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 0xFF:
                raise _Refusal("bad_request", "scan must be a scancode from 1 to 255")
        elif kind == "text":
            if not isinstance(value, str):
                raise _Refusal("bad_request", "text must be a string")
            if "\n" in value or "\r" in value:
                raise _Refusal("bad_text", "typed text must not hold a line break")
        elif kind == "wait_ms":
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise _Refusal("bad_request", "wait_ms must be a non-negative integer")
        else:
            raise _Refusal("bad_request", "unknown step %r" % kind)
        checked.append((kind, value))
    return checked


def _front_window(backend, state: State, pid: int, **fields) -> dict:
    """The game's window, which must be in front and its process the one recorded (`_prove_ours`); then look at
    the system's latest input, as close to the send as possible, so a person's key in the gap is seen and not
    written over by ours. Called before every step, character and press.

    The process is proved after the window has been looked up by its id and the foreground read, so the proof
    vouches for the window about to take the input as well; and it is raised first, so a process that is gone is
    `not_ours`, which no caller waits out, and never `not_foreground`."""
    win = _window(backend, pid)
    in_front = win is not None and backend.foreground_hwnd() == win["hwnd"]
    _prove_ours(backend, state, pid, **fields)
    if not in_front:
        raise _Refusal("not_foreground", "the game's window is not in front", **fields)
    _observe(backend, state)
    return win


def _clear_to_send(backend, state: State, pid: int, done: int, chars_sent: int = 0) -> None:
    _front_window(backend, state, pid, steps_done=done, chars_sent=chars_sent)


def _send_key(backend, state: State, send, argument) -> None:
    try:
        send(argument)
    finally:
        state.last_sent_tick = backend.tick()      # after the key-up, which lands later than the call starts


def _op_keys(req, backend, state):
    pid = _pid(req)
    steps = _steps(req)
    done = 0
    for kind, value in steps:
        if kind == "wait_ms":
            _clear_to_send(backend, state, pid, done)
            backend.sleep(value)
        elif kind == "scan":
            _clear_to_send(backend, state, pid, done)
            _send_key(backend, state, backend.send_scan, value)
        else:
            # A string takes about 10 ms a character and an Alt-Tab mid-string would type the rest into the
            # new window, so it goes a character at a time with the foreground checked before each.
            sent = 0
            for chunk in text_chunks(value):
                _clear_to_send(backend, state, pid, done, chars_sent=sent)
                if chunk:
                    _send_key(backend, state, backend.send_text, chunk)
                sent += len(chunk)
        done += 1
    return {"steps_done": done}


def _op_click(req, backend, state):
    pid, x, y = _pid(req), _int(req, "x"), _int(req, "y")
    left, top, width, height = _front_window(backend, state, pid)["client"]
    if not (0 <= x < width and 0 <= y < height):
        raise _Refusal("bad_point", "(%d, %d) is outside the %dx%d client area" % (x, y, width, height))
    target = (left + x, top + y)
    try:
        backend.set_cursor(*target)
        state.helper_cursor = backend.cursor_pos()      # where it is, not where it was sent: Windows may clamp it
        state.last_sent_tick = backend.tick()           # whether or not a cursor move counts as input, it was ours
        backend.sleep(CLICK_SETTLE_MS)
        # Everything can have changed while the cursor settled, so the press waits on a second look at all of it.
        win = _front_window(backend, state, pid)        # a window may have taken the front
        if tuple(win["client"]) != (left, top, width, height):
            raise _Refusal("bad_point", "the window moved or was resized while the cursor settled")
        if backend.cursor_pos() != target:              # clamped by the screen, or a person's hand
            raise _Refusal("cursor_misplaced", "the cursor is not at %s" % (target,))
        if backend.window_at(*target) != win["hwnd"]:   # another window, or none, is under the point
            raise _Refusal("covered", "the game's window is not the one under %s" % (target,))
        tap_button(backend.send_mouse, backend.sleep, CLICK_HOLD_MS)
    finally:
        state.last_sent_tick = backend.tick()           # after the button-up, which lands later than the call starts
    return {}


def _op_presence(req, backend, state):
    cursor = backend.cursor_pos()
    mine = state.helper_cursor
    return {"cursor": list(cursor), "foreground": backend.foreground_hwnd(),
            "helper_cursor": None if mine is None else list(mine)}


def _op_screenshot(req, backend, state):
    pid = _pid(req)
    path = _str(req, "path", empty=False)
    max_width = _int(req, "max_width", low=1, default=DEFAULT_MAX_WIDTH)
    win = _window(backend, pid)
    if win is None:
        raise _Refusal("no_window", "process %d has no window" % pid)
    x, y, w, h = win["client"]
    if w <= 0 or h <= 0:
        raise _Refusal("no_client_area", "the window's client area is empty (minimized?)")
    cw, ch, rgb = backend.capture((x, y, w, h))
    width, height, small = scale_rgb(cw, ch, rgb, max_width)
    data = encode_png(width, height, small)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return {"path": path, "width": width, "height": height}


def _op_kill(req, backend, state):
    pid = _pid(req)
    recorded = state.ours.get(pid)
    if recorded is None:
        raise _Refusal("not_ours", "process %d was not started by this helper" % pid)
    created = backend.creation_time(pid)
    if created is None:
        del state.ours[pid]         # it ended on its own: nothing to end, and its id may be reused from now on
        backend.forget_child(pid)   # so the handle that pinned the id can go too
        return {"already_exited": True}
    if created != recorded:
        raise _Refusal("not_ours", "process %d is not the one this helper started (its id was reused)" % pid)
    # The backend checks the creation time again through the handle it ends: no pid-reuse window.
    if not backend.terminate(pid, recorded):
        raise _Refusal("not_ours", "process %d changed under its id before it could be ended" % pid)
    del state.ours[pid]
    return {}


def _op_tcp_open(req, backend, state):
    port = _int(req, "port", low=1, high=65535)
    _close_socket(state)
    try:
        state.sock = backend.connect(LOOPBACK, port)        # the host is not a request field
    except OSError as e:
        raise _Refusal("connect_failed", repr(e))
    return {}


def _op_tcp_send(req, backend, state):
    text = _str(req, "b64")
    try:
        data = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        raise _Refusal("bad_request", "b64 is not base64")
    sock = _open_socket(state)
    try:
        sock.settimeout(SEND_TIMEOUT_S)
        sock.sendall(data)
    except OSError as e:
        _close_socket(state)
        raise _Refusal("tcp_closed", repr(e))
    return {}


def _op_tcp_recv(req, backend, state):
    timeout_ms = _int(req, "timeout_ms", low=0, default=DEFAULT_RECV_TIMEOUT_MS)
    sock = _open_socket(state)
    sock.settimeout(max(timeout_ms, 1) / 1000)
    try:
        data = sock.recv(RECV_BYTES)
    except socket.timeout:
        return {"b64": ""}
    except OSError as e:
        _close_socket(state)
        raise _Refusal("tcp_closed", repr(e))
    if not data:
        _close_socket(state)
        raise _Refusal("tcp_closed", "the peer closed the connection")
    return {"b64": base64.b64encode(data).decode("ascii")}


def _op_tcp_close(req, backend, state):
    _close_socket(state)
    return {}


_OPS = {
    "ping": _op_ping, "launch": _op_launch, "adopt": _op_adopt, "window": _op_window,
    "idle_ms": _op_idle_ms, "focus": _op_focus, "keys": _op_keys, "click": _op_click, "presence": _op_presence,
    "screenshot": _op_screenshot, "kill": _op_kill, "tcp_open": _op_tcp_open, "tcp_send": _op_tcp_send,
    "tcp_recv": _op_tcp_recv, "tcp_close": _op_tcp_close,
}


def handle(req, backend, state: State) -> dict:
    """One request to one reply. Never raises: a backend failure becomes `backend_error`."""
    rid = req.get("id") if isinstance(req, dict) else None
    try:
        if not isinstance(req, dict):
            raise _Refusal("bad_request", "a request is a JSON object")
        op = req.get("op")
        fn = _OPS.get(op) if isinstance(op, str) else None
        if fn is None:
            raise _Refusal("unknown_op", "unknown op %r" % (op,))
        return {"id": rid, "ok": True, **fn(req, backend, state)}
    except _Refusal as r:
        out = {"id": rid, "ok": False, "error": r.code}
        if r.detail:
            out["detail"] = r.detail
        out.update(r.fields)
        return out
    except Exception as e:      # the helper must outlive any one failing call
        return {"id": rid, "ok": False, "error": "backend_error", "detail": repr(e)}


def serve(stdin, stdout, backend, state: State) -> None:
    """Answer JSON lines from `stdin` on `stdout` (binary streams) until `stdin` closes."""
    try:
        while True:
            raw = stdin.readline()
            if not raw:
                break
            if not raw.strip():
                continue
            try:
                req = json.loads(raw.decode("utf-8"))
            except ValueError:
                reply = {"ok": False, "error": "bad_json"}
            else:
                reply = handle(req, backend, state)
            try:
                line = json.dumps(reply)
            except (TypeError, ValueError) as e:
                line = json.dumps({"id": reply.get("id"), "ok": False, "error": "backend_error", "detail": repr(e)})
            stdout.write(line.encode("ascii") + b"\n")         # ASCII only: the console code page cannot garble it
            stdout.flush()
    finally:
        _close_socket(state)


def main(stdin=None, stdout=None, backend=None) -> None:
    backend = backend if backend is not None else make_backend()
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    serve(stdin.buffer, stdout.buffer, backend, State())


def make_backend():
    if sys.platform != "win32":
        raise RuntimeError("win_helper drives Windows; run it with the Windows python.exe")
    return WindowsBackend()


class WindowsBackend:
    """Every Win32 call, ported from the PowerShell probe (docs/testing/game_qa_probe/powershell/lib.ps1).

    Built only on Windows. Methods take and return plain Python values; handles
    cross as ints (0 for none). Not exercised by the Linux tests: Task 9 proves it live.
    """

    PROCESS_TERMINATE = 0x0001
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    GW_OWNER = 4
    GA_ROOT = 2
    SW_RESTORE = 9
    VK_MENU = 0x12
    SRCCOPY = 0x00CC0020
    CAPTUREBLT = 0x40000000

    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        # A Popen object keeps a handle to its child open, which pins the child's pid against reuse while we hold it.
        self._children: dict[int, subprocess.Popen] = {}
        self._declare()
        self._user32.SetProcessDPIAware()       # client rectangles and captures in physical pixels

    def _declare(self) -> None:
        c = ctypes
        ptr, i32, u32, uint = c.c_void_p, c.c_int32, c.c_uint32, c.c_uint

        def sig(fn, restype, *argtypes):
            fn.restype, fn.argtypes = restype, list(argtypes)

        self._enum_proc = c.WINFUNCTYPE(i32, ptr, c.c_ssize_t)
        u, k, g = self._user32, self._kernel32, self._gdi32
        sig(u.SetProcessDPIAware, i32)
        sig(u.EnumWindows, i32, self._enum_proc, c.c_ssize_t)
        sig(u.GetWindowThreadProcessId, u32, ptr, c.POINTER(u32))
        sig(u.IsWindowVisible, i32, ptr)
        sig(u.GetWindow, ptr, ptr, uint)
        sig(u.GetWindowTextW, i32, ptr, c.c_wchar_p, i32)
        sig(u.GetClientRect, i32, ptr, c.POINTER(RECT))
        sig(u.ClientToScreen, i32, ptr, c.POINTER(POINT))
        sig(u.IsHungAppWindow, i32, ptr)
        sig(u.GetForegroundWindow, ptr)
        sig(u.SetForegroundWindow, i32, ptr)
        sig(u.ShowWindow, i32, ptr, i32)
        sig(u.IsIconic, i32, ptr)
        sig(u.SendInput, uint, uint, c.POINTER(INPUT), i32)
        sig(u.keybd_event, None, c.c_ubyte, c.c_ubyte, u32, c.c_size_t)
        sig(u.SetCursorPos, i32, i32, i32)
        sig(u.GetCursorPos, i32, c.POINTER(POINT))
        sig(u.WindowFromPoint, ptr, POINT)
        sig(u.GetAncestor, ptr, ptr, uint)
        sig(u.GetLastInputInfo, i32, c.POINTER(LASTINPUTINFO))
        sig(u.GetDC, ptr, ptr)
        sig(u.ReleaseDC, i32, ptr, ptr)
        sig(k.OpenProcess, ptr, u32, i32, u32)
        sig(k.CloseHandle, i32, ptr)
        sig(k.GetProcessTimes, i32, ptr, *([c.POINTER(FILETIME)] * 4))
        sig(k.GetExitCodeProcess, i32, ptr, c.POINTER(u32))
        sig(k.TerminateProcess, i32, ptr, uint)
        sig(k.GetTickCount64, c.c_uint64)
        sig(k.GetTickCount, u32)
        sig(g.CreateCompatibleDC, ptr, ptr)
        sig(g.CreateCompatibleBitmap, ptr, ptr, i32, i32)
        sig(g.SelectObject, ptr, ptr, ptr)
        sig(g.BitBlt, i32, ptr, i32, i32, i32, i32, ptr, i32, i32, u32)
        sig(g.GetDIBits, i32, ptr, ptr, uint, uint, ptr, c.POINTER(BITMAPINFO), uint)
        sig(g.DeleteObject, i32, ptr)
        sig(g.DeleteDC, i32, ptr)

    # -- processes

    def create_process(self, exe: str, args: list, cwd: str) -> int:
        # The game gets no standard handles: it must not write into the JSON channel
        # nor hold the pipe open after this helper is gone.
        proc = subprocess.Popen([exe, *args], cwd=cwd or None, close_fds=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._children[proc.pid] = proc
        return proc.pid

    def _created_of(self, handle) -> str | None:
        """The creation time of the live process behind `handle`, as an ISO string; None if it has exited."""
        code = ctypes.c_uint32(0)
        if self._kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value != self.STILL_ACTIVE:
            return None
        times = [FILETIME() for _ in range(4)]
        if not self._kernel32.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
            return None
        created = times[0]
        return filetime_to_iso((created.dwHighDateTime << 32) | created.dwLowDateTime)

    def creation_time(self, pid: int) -> str | None:
        handle = self._kernel32.OpenProcess(self.PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
        if not handle:
            return None
        try:
            return self._created_of(handle)
        finally:
            self._kernel32.CloseHandle(handle)

    def forget_child(self, pid: int) -> None:
        """Let go of the Popen (and its handle) kept for a child that has exited."""
        self._children.pop(pid, None)

    def terminate(self, pid: int, created: str) -> bool:
        """End `pid` only if the process behind the handle opened here was created at `created`."""
        handle = self._kernel32.OpenProcess(self.PROCESS_TERMINATE | self.PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
        if not handle:
            return False
        try:
            if self._created_of(handle) != created:
                return False
            if not self._kernel32.TerminateProcess(handle, 1):
                raise OSError("TerminateProcess failed (error %d)" % ctypes.get_last_error())
            self._children.pop(pid, None)
            return True
        finally:
            self._kernel32.CloseHandle(handle)

    # -- windows

    def _client(self, hwnd) -> tuple[int, int, int, int]:
        rect, origin = RECT(), POINT()
        self._user32.GetClientRect(hwnd, ctypes.byref(rect))
        self._user32.ClientToScreen(hwnd, ctypes.byref(origin))
        return (origin.x, origin.y, rect.right, rect.bottom)

    def window_of(self, pid: int) -> dict | None:
        """The process's main window: its visible top-level window with no owner and the largest client area."""
        user32, found = self._user32, []

        def visit(hwnd, lparam):
            owner = ctypes.c_uint32(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and user32.IsWindowVisible(hwnd) and not user32.GetWindow(hwnd, self.GW_OWNER):
                found.append(hwnd)
            return 1

        callback = self._enum_proc(visit)
        user32.EnumWindows(callback, 0)
        best = None
        for hwnd in found:
            client = self._client(hwnd)
            if best is None or client[2] * client[3] > best[1][2] * best[1][3]:
                best = (hwnd, client)
        if best is None:
            return None
        hwnd, client = best
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        return {"hwnd": int(hwnd), "title": title.value, "responding": not user32.IsHungAppWindow(hwnd),
                "client": client}

    def foreground_hwnd(self) -> int:
        return int(self._user32.GetForegroundWindow() or 0)

    def set_foreground(self, hwnd: int) -> tuple[bool, int | None]:
        """Bring `hwnd` to the front. Returns (in front afterwards, tick at which ALT was tapped or None).

        Plain `SetForegroundWindow` first: it works when the helper may take the foreground, and sends no
        input. Only if the window is still not in front is ALT tapped (the trick the probe used, which lets
        a second attempt through); a bare ALT lands in whatever window is in front, so it is the exception.
        """
        user32 = self._user32
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, self.SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.1)
        if self.foreground_hwnd() == hwnd:
            return True, None
        user32.keybd_event(self.VK_MENU, 0, 0, 0)
        user32.keybd_event(self.VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        tapped_at = self.tick()
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        return self.foreground_hwnd() == hwnd, tapped_at

    # -- input

    def _send(self, scan: int, flags: int) -> None:
        item = INPUT()
        item.type = INPUT_KEYBOARD
        item.ki.wVk = 0
        item.ki.wScan = scan
        item.ki.dwFlags = flags
        sent = self._user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT))
        if sent != 1:
            raise OSError("SendInput sent %d of 1 events (error %d): is another window's input blocking it?"
                          % (sent, ctypes.get_last_error()))

    def send_scan(self, scan: int) -> None:
        tap_key(self._send, time.sleep, scan, KEYEVENTF_SCANCODE, KEY_HOLD_S)
        time.sleep(KEY_HOLD_S)

    def send_text(self, text: str) -> None:
        for unit in utf16_units(text):
            tap_key(self._send, time.sleep, unit, KEYEVENTF_UNICODE, 0)       # the probe sent down and up back to back
            time.sleep(CHAR_GAP_S)

    def set_cursor(self, x: int, y: int) -> None:
        """Move the cursor to the screen point (x, y), in physical pixels (the process is DPI-aware)."""
        if not self._user32.SetCursorPos(x, y):
            raise OSError("SetCursorPos(%d, %d) failed (error %d)" % (x, y, ctypes.get_last_error()))

    def cursor_pos(self) -> tuple[int, int]:
        point = POINT()
        if not self._user32.GetCursorPos(ctypes.byref(point)):
            raise OSError("GetCursorPos failed (error %d)" % ctypes.get_last_error())
        return (point.x, point.y)

    def window_at(self, x: int, y: int) -> int:
        """The top-level window under the screen point (x, y): its handle, 0 if there is none."""
        child = self._user32.WindowFromPoint(POINT(x, y))
        if not child:
            return 0
        return int(self._user32.GetAncestor(child, self.GA_ROOT) or 0)

    def send_mouse(self, flags: int) -> None:
        """One mouse event (a MOUSEEVENTF_* button flag) at the cursor, where it is."""
        item = INPUT()
        item.type = INPUT_MOUSE
        item.mi.dwFlags = flags
        sent = self._user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT))
        if sent != 1:
            raise OSError("SendInput sent %d of 1 mouse events (error %d): is another window's input blocking it?"
                          % (sent, ctypes.get_last_error()))

    def tick(self) -> int:
        return int(self._kernel32.GetTickCount64())

    def last_input_tick(self) -> int:
        """When the system last saw keyboard or mouse input, on the same clock as `tick`.

        GetLastInputInfo reports the 32-bit tick count, which wraps every 49
        days, so its age is taken modulo 2**32 and subtracted from the 64-bit one
        (`last_input_tick_from`).
        """
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not self._user32.GetLastInputInfo(ctypes.byref(info)):
            raise OSError("GetLastInputInfo failed (error %d)" % ctypes.get_last_error())
        return last_input_tick_from(self.tick(), self._kernel32.GetTickCount(), info.dwTime)

    def sleep(self, ms: int) -> None:
        time.sleep(ms / 1000)

    # -- screen

    def capture(self, client: tuple[int, int, int, int]) -> tuple[int, int, bytes]:
        """The screen rectangle `client` (x, y, w, h) as (w, h, RGB bytes, top row first)."""
        x, y, w, h = client
        user32, gdi32 = self._user32, self._gdi32
        screen = user32.GetDC(None)
        if not screen:
            raise OSError("GetDC failed")
        memory = bitmap = None
        try:
            memory = gdi32.CreateCompatibleDC(screen)
            bitmap = gdi32.CreateCompatibleBitmap(screen, w, h)
            if not memory or not bitmap:
                raise OSError("could not create a bitmap of %dx%d" % (w, h))
            previous = gdi32.SelectObject(memory, bitmap)
            copied = gdi32.BitBlt(memory, 0, 0, w, h, screen, x, y, self.SRCCOPY | self.CAPTUREBLT)
            gdi32.SelectObject(memory, previous)        # GetDIBits wants the bitmap out of every DC
            if not copied:
                raise OSError("BitBlt failed (error %d)" % ctypes.get_last_error())
            info = BITMAPINFO()
            info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            info.bmiHeader.biWidth = w
            info.bmiHeader.biHeight = -h                # negative: top-down rows
            info.bmiHeader.biPlanes = 1
            info.bmiHeader.biBitCount = 32
            info.bmiHeader.biCompression = 0            # BI_RGB
            pixels = ctypes.create_string_buffer(w * h * 4)
            if gdi32.GetDIBits(memory, bitmap, 0, h, pixels, ctypes.byref(info), 0) != h:
                raise OSError("GetDIBits did not return %d rows" % h)
            bgra = pixels.raw
        finally:
            if bitmap:
                gdi32.DeleteObject(bitmap)
            if memory:
                gdi32.DeleteDC(memory)
            user32.ReleaseDC(None, screen)
        return w, h, bgra_to_rgb(w, h, bgra)

    # -- network

    def connect(self, host: str, port: int):
        return socket.create_connection((host, port), timeout=5)


if __name__ == "__main__":
    main()
