"""
event_image_inventory.py - What art each mod event actually shows.

Reads `events/*.txt` directly (no mod state server needed) and reports, per
event, whether it is hidden and what its `event_image` block(s) declare:

- ``texture``     one plain ``event_image = { texture = "..." }``
- ``video``       one plain ``event_image = { video = "..." }``
- ``conditional`` several ``event_image`` blocks, or one carrying a ``trigger``
- ``none``        no ``event_image`` (hidden events, or ``gui_window`` layouts)

``event_image_prompts.py --validate``, ``generate_event_images.py`` and
``test_event_image_registry.py`` use this to compare the prompt registry with
the event files, which are the source of truth.

Parsing follows ``event_image_audit.py``: a regex for top-level ``<id> = {``
definitions and brace matching for the block, so it runs in a sparse worktree
and in CI.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field

_DEF_RE = re.compile(r"^[ \t]*([a-z_][a-z0-9_]*\.\d+)[ \t]*=[ \t]*\{", re.M)
_HIDDEN_RE = re.compile(r"^[ \t]*hidden[ \t]*=[ \t]*yes\b", re.M)
_IMAGE_RE = re.compile(r"^[ \t]*event_image[ \t]*=[ \t]*\{", re.M)
_TEXTURE_RE = re.compile(r'\btexture\s*=\s*"([^"]+)"')
_VIDEO_RE = re.compile(r'\bvideo\s*=\s*"([^"]+)"')
_TRIGGER_RE = re.compile(r"\btrigger\s*=")
_PICTURE_RE = re.compile(r"^gfx/event_pictures/([^/]+)\.dds$")


@dataclass
class EventArt:
    event_id: str
    file: str  # path relative to the mod root, forward slashes
    hidden: bool
    blocks: list[dict] = field(default_factory=list)  # {"texture"|"video": value, "trigger": bool}

    @property
    def debug(self) -> bool:
        """Console-only test events (``events/te_debug_*.txt``)."""
        return os.path.basename(self.file).startswith("te_debug")

    @property
    def kind(self) -> str:
        if not self.blocks:
            return "none"
        if len(self.blocks) > 1 or self.blocks[0]["trigger"]:
            return "conditional"
        if "texture" in self.blocks[0]:
            return "texture"
        if "video" in self.blocks[0]:
            return "video"
        return "conditional"

    @property
    def picture(self) -> str | None:
        """The ``gfx/event_pictures/<name>.dds`` stem of a plain texture, else None."""
        if self.kind != "texture":
            return None
        m = _PICTURE_RE.match(self.blocks[0]["texture"])
        return m.group(1) if m else None


def _match_block(text: str, brace_pos: int) -> int:
    depth = 0
    for i in range(brace_pos, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def _strip_comments(text: str) -> str:
    # Event-image values never contain '#', so a plain cut is safe here.
    return re.sub(r"#[^\n]*", "", text)


def load(mod_root: str) -> dict[str, EventArt]:
    """Map every plainly defined mod event id to the art it declares."""
    events_dir = os.path.join(mod_root, "events")
    out: dict[str, EventArt] = {}
    for dirpath, _dirs, files in os.walk(events_dir):
        for fname in sorted(files):
            if not fname.endswith(".txt"):
                continue
            path = os.path.join(dirpath, fname)
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                text = _strip_comments(fh.read())
            rel = os.path.relpath(path, mod_root).replace(os.sep, "/")
            for m in _DEF_RE.finditer(text):
                brace = text.index("{", m.start())
                block = text[brace:_match_block(text, brace)]
                art = EventArt(m.group(1), rel, bool(_HIDDEN_RE.search(block)))
                for im in _IMAGE_RE.finditer(block):
                    ib = block.index("{", im.start())
                    body = block[ib:_match_block(block, ib)]
                    entry: dict = {"trigger": bool(_TRIGGER_RE.search(body))}
                    tm, vm = _TEXTURE_RE.search(body), _VIDEO_RE.search(body)
                    if tm:
                        entry["texture"] = tm.group(1)
                    elif vm:
                        entry["video"] = vm.group(1)
                    art.blocks.append(entry)
                out[art.event_id] = art
    return out


def pictures_on_disk(gfx_dir: str) -> set[str]:
    """Stems of the ``.dds`` files present in ``gfx/event_pictures``."""
    if not os.path.isdir(gfx_dir):
        return set()
    return {f[:-4] for f in os.listdir(gfx_dir) if f.endswith(".dds")}


def committed_pictures(mod_root: str) -> set[str]:
    """Stems of the ``.dds`` files git tracks in ``gfx/event_pictures``.

    Works in a sparse worktree that leaves ``gfx/`` unchecked-out.
    """
    out = subprocess.run(
        ["git", "-C", mod_root, "ls-files", "--", "gfx/event_pictures/*.dds"],
        capture_output=True, text=True, check=True).stdout
    return {os.path.basename(line)[:-4] for line in out.splitlines() if line}


def known_pictures(mod_root: str) -> set[str]:
    """The pictures on disk, or git's list when ``gfx/`` is not checked out."""
    gfx_dir = os.path.join(mod_root, "gfx", "event_pictures")
    if os.path.isdir(gfx_dir):
        return pictures_on_disk(gfx_dir)
    return committed_pictures(mod_root)
