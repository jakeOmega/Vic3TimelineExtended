"""Tests for the event-image prompt registry and generate_event_images phase 3.

The registry (scripts/image_pipeline/event_image_prompts.py) lists, per
picture, the events that show it. Phase 3 of generate_event_images.py rewrites
every listed event to its listed picture, so a stale list silently reverts
events that were re-pointed by hand. In September 2026 the list had drifted on
45 events and named 30 deleted ones; these tests keep it honest.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MOD_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MOD_ROOT, "scripts", "image_pipeline"))

import event_image_inventory as inv  # noqa: E402
import event_image_prompts as eip  # noqa: E402
import generate_event_images as gei  # noqa: E402


class RegistryMatchesEventFilesTests(unittest.TestCase):
    """The committed registry agrees with the committed event files."""

    @classmethod
    def setUpClass(cls):
        try:
            pictures = inv.committed_pictures(MOD_ROOT)
        except (OSError, subprocess.CalledProcessError):
            raise unittest.SkipTest("git is unavailable")
        cls.report = eip.check(inv.load(MOD_ROOT), pictures)

    def test_no_event_listed_under_two_pictures(self):
        self.assertEqual(self.report["duplicates"], [])

    def test_listed_events_exist_and_are_visible(self):
        self.assertEqual(
            self.report["dead"], [],
            "Drop these IDs from event_image_prompts.IMAGES (event gone, hidden, "
            "or a console-only te_debug event).")

    def test_listed_events_show_their_picture(self):
        self.assertEqual(
            self.report["drift"], [],
            "These events show a different picture from the one they are listed "
            "under, so `generate_event_images.py --phase update` would revert them. "
            "Move each ID to the list of the picture it now shows (or drop it if "
            "that picture has no entry). `python3 scripts/image_pipeline/"
            "event_image_prompts.py --validate` prints the full report.")


class PhaseUpdateTests(unittest.TestCase):
    """generate_event_images._update_event_file and _build_event_to_texture."""

    def _file(self, text: str) -> Path:
        d = tempfile.mkdtemp()
        p = Path(d) / "e.txt"
        p.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        return p

    def test_pending_picture_leaves_its_events_alone(self):
        images = {"new_pic": {"prompt": "", "events": ["my.1"]},
                  "old_pic": {"prompt": "", "events": ["my.2"]}}
        mapping, pending = gei._build_event_to_texture(images, {"old_pic"})
        self.assertEqual(pending, ["new_pic"])
        self.assertEqual(mapping, {"my.2": "gfx/event_pictures/old_pic.dds"})

    def test_listed_event_is_repointed_and_bom_kept(self):
        p = self._file(
            'namespace = my\nmy.1 = {\n\ttype = country_event\n'
            '\tevent_image = { video = "unspecific_trains" }\n}\n')
        changed, skipped = gei._update_event_file(
            p, {"my.1": "gfx/event_pictures/pic.dds"})
        self.assertEqual((changed, skipped), (1, []))
        raw = p.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b'\tevent_image = { texture = "gfx/event_pictures/pic.dds" }\n', raw)
        self.assertNotIn(b"unspecific_trains", raw)

    def test_event_already_showing_its_picture_is_untouched(self):
        text = ('my.1 = {\n\tevent_image = {\n\t\ttexture = "gfx/event_pictures/pic.dds"\n'
                '\t}\n\ttitle = my.1.t\n}\n')
        p = self._file(text)
        before = p.read_bytes()
        changed, _ = gei._update_event_file(p, {"my.1": "gfx/event_pictures/pic.dds"})
        self.assertEqual(changed, 0)
        self.assertEqual(p.read_bytes(), before)

    def test_multiline_block_is_replaced_whole(self):
        p = self._file('my.1 = {\n\tevent_image = {\n\t\ttexture = "gfx/event_pictures/a.dds"\n'
                       '\t}\n\ttitle = my.1.t\n}\n')
        changed, _ = gei._update_event_file(p, {"my.1": "gfx/event_pictures/b.dds"})
        self.assertEqual(changed, 1)
        self.assertEqual(
            p.read_bytes().decode("utf-8-sig"),
            'my.1 = {\n\tevent_image = { texture = "gfx/event_pictures/b.dds" }\n'
            '\ttitle = my.1.t\n}\n')

    def test_conditional_art_is_skipped(self):
        text = (
            'my.1 = {\n'
            '\tevent_image = { trigger = { has_variable = x } texture = "gfx/event_pictures/a.dds" }\n'
            '\tevent_image = { texture = "gfx/event_pictures/b.dds" }\n'
            '}\n'
            'my.2 = {\n'
            '\tevent_image = {\n\t\ttrigger = { always = yes }\n\t\tvideo = "unspecific_fire"\n\t}\n'
            '}\n')
        p = self._file(text)
        before = p.read_bytes()
        changed, skipped = gei._update_event_file(
            p, {"my.1": "gfx/event_pictures/c.dds", "my.2": "gfx/event_pictures/c.dds"})
        self.assertEqual((changed, skipped), (0, ["my.1", "my.2"]))
        self.assertEqual(p.read_bytes(), before)

    def test_unlisted_event_is_untouched(self):
        p = self._file('my.1 = {\n\tevent_image = { texture = "gfx/event_pictures/a.dds" }\n}\n'
                       'my.2 = {\n\tevent_image = { texture = "gfx/event_pictures/a.dds" }\n}\n')
        changed, _ = gei._update_event_file(p, {"my.2": "gfx/event_pictures/b.dds"})
        self.assertEqual(changed, 1)
        text = p.read_bytes().decode("utf-8-sig")
        self.assertIn('my.1 = {\n\tevent_image = { texture = "gfx/event_pictures/a.dds" }', text)
        self.assertIn('my.2 = {\n\tevent_image = { texture = "gfx/event_pictures/b.dds" }', text)


class InventoryTests(unittest.TestCase):
    def test_kinds(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "events"))
        with open(os.path.join(d, "events", "e.txt"), "w", encoding="utf-8-sig") as f:
            f.write(
                'my.1 = {\n\tevent_image = { texture = "gfx/event_pictures/a.dds" } # note\n}\n'
                'my.2 = {\n\thidden = yes\n}\n'
                'my.3 = {\n\tevent_image = { video = "unspecific_fire" }\n}\n'
                'my.4 = {\n\tevent_image = { trigger = { always = yes } texture = "x.dds" }\n}\n'
                '# my.5 = {\n')
        arts = inv.load(d)
        self.assertEqual(sorted(arts), ["my.1", "my.2", "my.3", "my.4"])
        self.assertEqual((arts["my.1"].kind, arts["my.1"].picture), ("texture", "a"))
        self.assertEqual((arts["my.2"].hidden, arts["my.2"].kind), (True, "none"))
        self.assertEqual(arts["my.3"].kind, "video")
        self.assertEqual((arts["my.4"].kind, arts["my.4"].picture), ("conditional", None))


if __name__ == "__main__":
    unittest.main()
