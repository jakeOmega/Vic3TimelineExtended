"""Tests for game_qa.gui_preview: what `gui-show` syncs, which types it takes, the wrapper it writes and the log it
reads back (spec docs/superpowers/specs/2026-11-23-gui-preview-design.md)."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from game_qa import gui_preview


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def write(repo: Path, rel: str, text: str = "x = {}\n") -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


class RepoCase(unittest.TestCase):
    """A throwaway repo: `main` with a first commit, `origin/main` on it, and the branch `work` checked out."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.invalid")
        git(self.repo, "config", "user.name", "test")
        for rel in ("gui/b.gui", "gui/old.gui", "gui/main_only.gui", "common/scripted_guis/x.txt",
                    "common/script_values/y.txt", "localization/english/z.yml", "events/e.txt"):
            write(self.repo, rel)
        commit(self.repo, "first")
        git(self.repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        self.base = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "-q", "-b", "work")
        self.plain = Path(tmp.name) / "plain"
        self.plain.mkdir()


class BranchChangesTest(RepoCase):
    def test_committed_uncommitted_and_untracked_gui_files_are_taken(self):
        write(self.repo, "gui/a.gui")
        commit(self.repo, "a")
        write(self.repo, "gui/b.gui", "y = {}\n")
        write(self.repo, "gui/sub/c.gui")
        ch = gui_preview.branch_changes(self.repo)
        self.assertEqual(ch.gui, ["gui/a.gui", "gui/b.gui", "gui/sub/c.gui"])
        self.assertEqual(ch.base, self.base)

    def test_files_main_changed_after_the_branch_point_are_not_taken(self):
        git(self.repo, "checkout", "-q", "main")
        write(self.repo, "gui/main_only.gui", "changed = {}\n")
        commit(self.repo, "main moves on")
        git(self.repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(self.repo, "checkout", "-q", "work")
        write(self.repo, "gui/a.gui")
        commit(self.repo, "a")
        ch = gui_preview.branch_changes(self.repo)
        self.assertNotIn("gui/main_only.gui", ch.gui)
        self.assertEqual(ch.gui, ["gui/a.gui"])

    def test_deleted_and_non_gui_files_are_left_out(self):
        (self.repo / "gui/old.gui").unlink()
        write(self.repo, "gui/notes.txt")
        write(self.repo, "gfx/x.dds")
        commit(self.repo, "delete and add")
        self.assertEqual(gui_preview.branch_changes(self.repo).gui, [])

    def test_script_side_changes_are_listed_apart(self):
        for rel in ("common/scripted_guis/x.txt", "common/script_values/y.txt", "localization/english/z.yml",
                    "events/e.txt"):
            write(self.repo, rel, "changed = {}\n")
        self.assertEqual(gui_preview.branch_changes(self.repo).script, [
            "common/script_values/y.txt", "common/scripted_guis/x.txt", "localization/english/z.yml"])

    def test_no_upstream_is_not_a_repo(self):
        git(self.repo, "update-ref", "-d", "refs/remotes/origin/main")
        for path in (self.repo, self.plain):
            with self.subTest(path=path.name):
                with self.assertRaises(gui_preview.PreviewError) as caught:
                    gui_preview.branch_changes(path)
                self.assertEqual(caught.exception.code, "not_a_repo")


if __name__ == "__main__":
    unittest.main()
