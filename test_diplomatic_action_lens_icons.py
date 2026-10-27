"""Every mod diplomatic action shown in the lens bar ships its lens icon.

The engine loads gfx/interface/icons/lens_toolbar_icons/<action>.dds for every
diplomatic action without `show_in_lens = no`, whatever `texture =` says
(scripting_best_practices.md, the lens toolbar note). A missing file logs a
VFSOpen error each session and the lens button draws with no icon:
Administer Seabed Claims shipped that way (2026-10-17). CI checks out without
gfx/, so a texture counts when git tracks it.
"""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIONS = ROOT / "common/diplomatic_actions"
LENS = "gfx/interface/icons/lens_toolbar_icons"

# Actions still on another action's art until an icon pass draws their own
# (test_covert_op_registry.PLACEHOLDER_ICON).
PENDING = set()


def tracked(path: str) -> bool:
    if (ROOT / path).is_file():
        return True
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", path], cwd=ROOT, capture_output=True
    ).returncode == 0


def lens_actions() -> dict[str, str]:
    """Top-level action keys without show_in_lens = no -> their file."""
    found = {}
    for path in sorted(ACTIONS.glob("*.txt")):
        depth = 0
        key = None
        body = []
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.split("#", 1)[0]
            if depth == 0:
                match = re.match(r"\s*([A-Za-z0-9_]+)\s*=\s*\{", line)
                if match:
                    key, body = match.group(1), []
            if key:
                body.append(line)
            depth += line.count("{") - line.count("}")
            if key and depth == 0:
                if not re.search(r"\bshow_in_lens\s*=\s*no\b", "\n".join(body)):
                    found[key] = path.name
                key = None
    return found


class LensIconTest(unittest.TestCase):
    def test_the_scan_finds_actions(self):
        actions = lens_actions()
        self.assertIn("te_seabed_administer_claims", actions)
        self.assertIn("covert_cultivate_assets_action", actions)

    def test_every_lens_action_has_its_icon(self):
        for action, source in lens_actions().items():
            if action in PENDING:
                continue
            with self.subTest(action=action, file=source):
                self.assertTrue(tracked(f"{LENS}/{action}.dds"), f"{LENS}/{action}.dds")

    def test_pending_entries_are_still_pending(self):
        actions = lens_actions()
        for action in PENDING:
            with self.subTest(action=action):
                self.assertIn(action, actions, "the action is gone: drop it from PENDING")
                self.assertFalse(
                    tracked(f"{LENS}/{action}.dds"), "the icon has landed: drop it from PENDING"
                )


if __name__ == "__main__":
    unittest.main()
