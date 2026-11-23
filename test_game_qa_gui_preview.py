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


X_GUI = """types x_types {
	type te_x_section = flowcontainer {}
	type te_x_table = widget {}
	type te_x_help_body = widget {}
	type te_x_wrapper = flowcontainer {}
	type te_x_inner = widget {}
	type te_x_help_popup = te_ui_help_popup {
		blockoverride "popup_title" {
			text = "x"
		}
		blockoverride "popup_list" {
			vanilla_box = {
				te_x_help_body = {}
			}
		}
	}
}

widget = {
	name = "widget_je_x_status"
	flowcontainer = {
		te_x_section = {}
		textbox = { text = "x" }
		widget = {
			te_x_table = {}
		}
		te_x_section = {}
		te_x_wrapper = {
			te_x_inner = {}
		}
	}
}
"""
LIB_GUI = """types lib {
	type te_ui_popup = widget {}
	type te_ui_help_popup = te_ui_popup {}
}
"""
JE_X = """je_x = {
	widget = {
		gui = "gui/x.gui"
		name = "widget_je_x_status"
		container = "custom_widget_container_1"
	}
}
"""


class CheckTypeTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo, game = Path(tmp.name) / "repo", Path(tmp.name) / "game"
        write(repo, "gui/x.gui", X_GUI)
        write(repo, "gui/lib.gui", LIB_GUI)
        write(repo, "common/journal_entries/je_x.txt", JE_X)
        write(game, "game/gui/v.gui", "types v {\n\ttype vanilla_only_type = widget {}\n\ttype vanilla_box = widget {}\n}\n")
        self.idx = gui_preview.gui_index(repo, game)

    def error_of(self, name):
        with self.assertRaises(gui_preview.PreviewError) as caught:
            gui_preview.check_type(name, self.idx)
        return caught.exception

    def test_a_mod_type_passes(self):
        gui_preview.check_type("te_x_section", self.idx)

    def test_a_vanilla_type_passes(self):
        gui_preview.check_type("vanilla_only_type", self.idx)

    def test_an_unknown_type_is_refused(self):
        self.assertEqual(self.error_of("te_nothing").code, "unknown_type")

    def test_a_name_that_cannot_be_typed_is_refused(self):
        for bad in ("", "a b", "x;y", "x'y", "1abc"):
            with self.subTest(bad=bad):
                self.assertEqual(self.error_of(bad).code, "bad_argument")

    def test_a_journal_entrys_root_is_refused_with_its_sections(self):
        e = self.error_of("widget_je_x_status")
        self.assertEqual(e.code, "je_root")
        # an instance's own written content is the root's too (te_je_country = { te_tax_status_sections = {} })
        self.assertEqual(e.info["hint"], ["te_x_section", "te_x_table", "te_x_wrapper", "te_x_inner"])

    def test_a_popup_shell_is_refused_with_its_body(self):
        e = self.error_of("te_x_help_popup")
        self.assertEqual(e.code, "popup_shell")
        self.assertEqual(e.info["hint"], ["te_x_help_body"])         # the mod's types only, not vanilla_box


if __name__ == "__main__":
    unittest.main()
