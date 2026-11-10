"""Follow one of the game's logs across rotation, and read console and debug_log lines.

The game keeps six generations of a log (`debug.log`, `debug.1.log` …
`debug.5.log`, about 524 KB each) and writes in blocks of about 4 KB that can
end in the middle of a line. A hot reload has been seen to fill all six
generations in one second (spec § 3.3), so a reader that looks afterwards
finds nothing: `LogFollower` is polled for the whole run and keeps its place
by the first bytes of the file it was reading.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

GAP_MARKER = "<<game_qa: log lines lost in rotation>>"
GENERATIONS = 5
_HEAD_BYTES = 64


class LogFollower:
    """`poll()` returns the complete lines written since the last call, oldest
    first, each exactly once. A last line with no newline yet is held back.

    The file being read is known by its inode, which a rename keeps (rotation
    renames `debug.log` to `debug.1.log`). Its first bytes are the fallback:
    they cannot be the main test, because during a reload flood every
    generation starts with the same repeated line."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._offset = 0
        self._ino: int | None = None
        self._head = b""
        self._partial = b""

    def _generation(self, k: int) -> Path:
        return self.path.with_name(f"{self.path.stem}.{k}{self.path.suffix}")

    @staticmethod
    def _read(path: Path, start: int = 0) -> bytes:
        try:
            with open(path, "rb") as f:
                f.seek(start)
                return f.read()
        except OSError:
            return b""

    @staticmethod
    def _read_head(path: Path) -> bytes:
        try:
            with open(path, "rb") as f:
                return f.read(_HEAD_BYTES)
        except OSError:
            return b""

    @staticmethod
    def _stat(path: Path) -> tuple[int | None, int]:
        try:
            st = path.stat()
        except OSError:
            return None, -1
        return st.st_ino, st.st_size

    def _same_inode(self, path: Path) -> bool:
        """Same inode, and still the same first bytes: a filesystem hands a
        deleted file's inode to the next file created."""
        ino, size = self._stat(path)
        if ino is None or ino != self._ino or size < self._offset:
            return False
        return self._read_head(path)[: len(self._head)] == self._head

    def _same_head(self, path: Path) -> bool:
        if not self._head or self._stat(path)[1] < self._offset:
            return False
        return self._read_head(path)[: len(self._head)] == self._head

    def _find_mine(self) -> int | None:
        """The numbered generation that is the file this follower was reading."""
        for test in (self._same_inode, self._same_head):
            for k in range(1, GENERATIONS + 1):
                if test(self._generation(k)):
                    return k
        return None

    def poll(self) -> list[str]:
        lines: list[str] = []
        if self._ino is not None and not self._same_inode(self.path):
            mine = self._find_mine()
            if mine is None:
                # Its file fell off the end: what it had not read is gone.
                self._partial = b""
                lines.append(GAP_MARKER)
                chunks = [self._read(self._generation(k)) for k in range(GENERATIONS, 0, -1)]
            else:
                chunks = [self._read(self._generation(mine), self._offset)]
                chunks.extend(self._read(self._generation(k)) for k in range(mine - 1, 0, -1))
            for chunk in chunks:
                lines.extend(self._lines(chunk))
            self._offset = 0
            self._ino = None
            self._head = b""
        ino, _size = self._stat(self.path)
        if ino is None:
            return lines
        data = self._read(self.path, self._offset)
        lines.extend(self._lines(data))
        self._offset += len(data)
        self._ino = ino
        if len(self._head) < _HEAD_BYTES:
            self._head = self._read_head(self.path)
        return lines

    def _lines(self, data: bytes) -> list[str]:
        buf = self._partial + data
        pieces = buf.split(b"\n")
        self._partial = pieces.pop()
        return [p.rstrip(b"\r").decode("utf-8", errors="replace") for p in pieces]


@dataclass
class Parsed:
    time: str
    kind: str  # "command" | "success" | "failure" | "debug_log" | "other"
    text: str
    file: str | None = None
    lineno: int | None = None


_LINE = re.compile(r"^\[(\d\d:\d\d:\d\d)\]\[([^\]:]+):\d+\]: (.*)$")
_SCRIPT_AT = re.compile(r"^(\S+\.(?:txt|gui|yml)):(\d+): (.*)$")
_CONSOLE = (
    ("Running console command: ", "command"),
    ("console_success: ", "success"),
    ("console_failure: ", "failure"),
)


def parse(line: str) -> Parsed:
    """Classify one log line. The cpp file's name decides, not its line number,
    which moves between patches."""
    m = _LINE.match(line)
    if not m:
        return Parsed("", "other", line)
    when, source, message = m.groups()
    if source == "console.cpp":
        for prefix, kind in _CONSOLE:
            if message.startswith(prefix):
                return Parsed(when, kind, message[len(prefix):])
    elif source == "jomini_effect_impl.cpp":
        at = _SCRIPT_AT.match(message)
        if at:
            return Parsed(when, "debug_log", at.group(3), at.group(1), int(at.group(2)))
    return Parsed(when, "other", message)


@dataclass(frozen=True)
class Pending:
    numeric_id: int
    event_id: str
    options: int


_PENDING = re.compile(r"^(\d+) (\S+) options=(\d+)$")


def pending_events(reply_lines: Sequence[str]) -> list[Pending]:
    """The reply of `select_event_option list`: one `<numeric id> <event id>
    options=<n>` line per pending event, or "No pending events"."""
    found = []
    for line in reply_lines:
        m = _PENDING.match(line.strip())
        if m:
            found.append(Pending(int(m.group(1)), m.group(2), int(m.group(3))))
    return found
