"""Follow one of the game's logs across rotation, and read console and debug_log lines.

The game keeps six generations of a log (`debug.log`, `debug.1.log` …
`debug.5.log`, about 524 KB each) and writes in blocks of about 4 KB that can
end in the middle of a line. A hot reload has been seen to fill all six
generations in one second (spec § 3.3), so a reader that looks afterwards
finds nothing: `LogFollower` is polled for the whole run and keeps its place
by the inode of the file it was reading, which a rename keeps. A flood makes
every generation begin with the same repeated line, so the first bytes of a
file never tell it from another one: they are consulted only when the live
file kept the inode and shrank (a rotation that copies and truncates), and as
a guard against a filesystem handing a deleted file's inode to a new one.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Sequence

GAP_MARKER = "<<game_qa: log lines lost in rotation>>"
GENERATIONS = 5
_HEAD_BYTES = 64
_ATTEMPTS = 4           # looks at the files, when a rotation keeps changing them under the look


@dataclass
class _Held:
    """A file opened once: everything known about it comes from this one descriptor, so a rename after the
    open changes none of it."""
    f: BinaryIO
    ino: int
    size: int

    def head(self, size: int = _HEAD_BYTES) -> bytes:
        self.f.seek(0)
        return self.f.read(size)

    def read_from(self, start: int) -> bytes:
        self.f.seek(start)
        return self.f.read()


class LogFollower:
    """`poll()` returns the complete lines written since the last call, oldest
    first, each exactly once. A last line with no newline yet is held back.

    The file being read is known by its inode, which a rename keeps (rotation
    renames `debug.log` to `debug.1.log`), and each poll opens a file once and
    takes its inode, its size and its data from that one descriptor. When the
    inode is not among the live file and the generations, the file fell off
    the end: the poll puts `GAP_MARKER` first and reads what is left. While
    there is no live file, the follower stays on the newest generation it
    read, so a file that appears and rotates before the next poll is not
    skipped."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._offset = 0
        self._ino: int | None = None
        self._head = b""
        self._partial = b""

    def _generation(self, k: int) -> Path:
        return self.path.with_name(f"{self.path.stem}.{k}{self.path.suffix}")

    @staticmethod
    def _open(path: Path, held: list[BinaryIO]) -> _Held | None:
        """The file opened once, or None. It is closed with the rest of `held` when the poll is over."""
        try:
            f = open(path, "rb")
        except OSError:
            return None
        held.append(f)
        try:
            st = os.fstat(f.fileno())
        except OSError:
            return None
        return _Held(f, st.st_ino, st.st_size)

    def _is_mine(self, file: _Held) -> bool:
        """Same inode, and still the same first bytes: a filesystem hands a deleted file's inode to the next
        file created."""
        return file.ino == self._ino and file.size >= self._offset and file.head(len(self._head)) == self._head

    def _same_head(self, file: _Held) -> bool:
        return bool(self._head) and file.size >= self._offset and file.head(len(self._head)) == self._head

    def _find_mine(self, generations: list[tuple[int, _Held]], truncated: bool) -> int | None:
        """The numbered generation that is the file this follower was reading. The first bytes are asked only
        when the live file kept our inode and shrank (copy and truncate): after a rename they would match any
        generation of a flood."""
        for test in (self._is_mine, self._same_head) if truncated else (self._is_mine,):
            for k, file in generations:
                if test(file):
                    return k
        return None

    def poll(self) -> list[str]:
        for _ in range(_ATTEMPTS):
            held: list[BinaryIO] = []
            try:
                lines = self._poll_once(held)
            finally:
                for f in held:
                    f.close()
            if lines is not None:
                return lines
        return []           # the files kept moving; nothing was consumed, the next poll looks again

    def _poll_once(self, held: list[BinaryIO]) -> list[str] | None:
        """One look at the files, or None if a rotation raced the look (and then nothing has been consumed)."""
        live = self._open(self.path, held)
        if self._ino is None:
            return self._take(live, 0) if live is not None else []
        if live is not None and self._is_mine(live):
            return self._take(live, self._offset)
        truncated = live is not None and live.ino == self._ino
        # The live file was opened first: if it is a generation by now, a rotation came between, and the look
        # has to be made again (it would be read twice, and a newer live file would be missed).
        generations: list[tuple[int, _Held]] = []
        for k in range(1, GENERATIONS + 1):
            file = self._open(self._generation(k), held)
            if file is not None:
                generations.append((k, file))
        inodes = [file.ino for _k, file in generations] + ([live.ino] if live is not None else [])
        if len(set(inodes)) != len(inodes):
            return None
        mine = self._find_mine(generations, truncated)
        lines: list[str] = []
        if mine is None:
            # Its file fell off the end: what it had not read is gone.
            self._partial = b""
            lines.append(GAP_MARKER)
            unread = [(file, 0) for _k, file in reversed(generations)]
        else:
            unread = [(file, self._offset if k == mine else 0) for k, file in reversed(generations) if k <= mine]
        anchor: tuple[int, int, bytes] | None = None
        for file, start in unread:
            data = file.read_from(start)
            lines.extend(self._lines(data))
            anchor = (file.ino, start + len(data), file.head())
        if live is not None:
            self._ino, self._offset, self._head = None, 0, b""      # the live file follows them: from its start
            lines.extend(self._take(live, 0))
        elif anchor is not None:
            # No live file yet: stay on the newest file read, so a new one that rotates before the next poll
            # is found behind it.
            self._ino, self._offset, self._head = anchor
        else:
            self._ino, self._offset, self._head = None, 0, b""
        return lines

    def _take(self, file: _Held, start: int) -> list[str]:
        """Read `file` from `start` and make it the file being followed."""
        data = file.read_from(start)
        self._ino, self._offset = file.ino, start + len(data)
        if len(self._head) < _HEAD_BYTES:
            self._head = file.head()
        return self._lines(data)

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
