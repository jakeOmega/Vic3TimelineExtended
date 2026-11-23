"""`gui-show`'s pure parts: what a preview syncs, which types it takes, the wrapper it writes and the GUI lines it
reads back (spec docs/superpowers/specs/2026-11-23-gui-preview-design.md).

A preview shows one GUI type from the caller's working tree, alone, in the running game: the session copies the
`.gui` files the caller's branch changed into the overlay, rewrites the overlay's wrapper (a full-screen magenta
backdrop and a centred window that instances the type), waits for the game to log the wrapper's revision, and
recreates the widget with the console. Nothing here touches the game or the overlay; `overlay.py` writes and
`session.py` drives.

The files are the branch's, not "every file that differs from the deployed copy": a worktree branched from an
older `main` differs in every file `main` changed since, and syncing those would lay the branch's older copies over
the deployed build for the rest of the session (spec § 5.2, step 1).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIRS = ("common/scripted_guis/", "common/script_values/", "localization/")


class PreviewError(Exception):
    """A preview that cannot go ahead. `code` names why; `info` holds what goes with it (a `hint`, a `file`)."""

    def __init__(self, code: str, detail: str = "", **info: Any) -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail, self.info = code, detail, info


@dataclass(frozen=True)
class BranchChanges:
    base: str           # the merge base with the upstream, which the changes are measured from
    gui: list[str]      # the `.gui` files under gui/ the branch changed, committed or not, that exist now
    script: list[str]   # the files under SCRIPT_DIRS it changed: a preview reads the deployed versions of these


def _git(repo: Path, *args: str) -> str:
    cmd = ["git", "-C", str(repo), *args]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise PreviewError("not_a_repo", "%s failed: %s" % (" ".join(cmd), e)) from e
    if done.returncode != 0:
        raise PreviewError("not_a_repo", "%s failed: %s" % (" ".join(cmd), done.stderr.strip()))
    return done.stdout


def branch_changes(repo: Path, upstream: str = "origin/main") -> BranchChanges:
    """The files the branch checked out in `repo` changed against its merge base with `upstream`: its commits, its
    uncommitted edits and its untracked files. A file deleted since is left out (there is nothing to sync).
    `PreviewError("not_a_repo")` when `repo` is not a checkout or has no `upstream`."""
    repo = Path(repo)
    base = _git(repo, "merge-base", "HEAD", upstream).strip()
    changed = set(_git(repo, "diff", "--name-only", base).splitlines())
    changed |= set(_git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
    present = sorted(rel for rel in changed if rel and (repo / rel).is_file())
    gui = [rel for rel in present if rel.startswith("gui/") and rel.endswith(".gui")]
    script = [rel for rel in present if rel.startswith(SCRIPT_DIRS)]
    return BranchChanges(base, gui, script)
