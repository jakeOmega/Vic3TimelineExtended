"""Tests for the UI icon pipeline (scripts/image_pipeline/generate_icons.py).

The registry (icon_prompts.py) must name real mod entities, and an accepted
icon must be committed; `wire` must change only the icon line of the entities
it is told about; the DDS writer must produce vanilla's layout (checked
byte-for-byte against invention_icons/mass_communication.dds's header). The
rendering itself needs a GPU and is not tested here.
"""

import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

MOD_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(MOD_ROOT, "scripts", "image_pipeline"))

import generate_icons as gi  # noqa: E402
import icon_prompts as ip  # noqa: E402

try:
    import numpy as np
    from PIL import Image

    import icon_dds
except ImportError:  # CI installs numpy but not Pillow
    icon_dds = None


class RegistryTests(unittest.TestCase):
    def test_registry_matches_the_mod(self):
        try:
            report = ip.check()
        except (OSError, Exception) as e:  # git unavailable
            raise unittest.SkipTest(f"git unavailable: {e}")
        self.assertEqual(report["unknown"], [], "keys with no top-level definition in entity_dir")
        self.assertEqual(report["bad_entry"], [], "empty subject, or seed not None/int/'keep'")
        self.assertEqual(report["missing_dds"], [],
                         "accepted icons whose DDS is not committed: run generate_icons.py --stage write")

    def test_every_generated_category_names_its_entities(self):
        for cat in ip.ICONS:
            self.assertIn("entity_dir", ip.CATEGORIES[cat])
            self.assertIn("field", ip.CATEGORIES[cat])

    def test_check_flags_bad_entries(self):
        saved = ip.ICONS
        try:
            ip.ICONS = {"technology": {
                "ok": {"subject": "a brass gear", "seed": None},
                "kept": {"subject": "a brass gear", "seed": ip.KEEP},
                "accepted": {"subject": "a brass gear", "seed": 1},
                "no_subject": {"subject": "", "seed": None},
                "bad_seed": {"subject": "a brass gear", "seed": "1"},
                "nowhere": {"subject": "a brass gear", "seed": None},
                "reuses": {"use": "gfx/interface/icons/invention_icons/radio.dds"},
                "bad_use": {"use": "radio.dds"},
            }}
            d = tempfile.mkdtemp()
            tech_dir = Path(d) / "common" / "technology" / "technologies"
            tech_dir.mkdir(parents=True)
            (tech_dir / "t.txt").write_text(
                "".join(f"{k} = {{\n\tera = era_6\n}}\n"
                        for k in ("ok", "kept", "accepted", "no_subject", "bad_seed", "reuses", "bad_use")),
                encoding="utf-8-sig")
            r = ip.check(d, on_disk=set())
        finally:
            ip.ICONS = saved
        self.assertEqual(r["unknown"], [("technology", "nowhere")])
        self.assertEqual(sorted(r["bad_entry"]), [("technology", "bad_seed"), ("technology", "bad_use"),
                                                  ("technology", "no_subject")])
        self.assertEqual(r["missing_dds"], [("technology", "accepted")])
        self.assertEqual(r["states"]["technology"],
                         {"unreviewed": 2, "accepted": 1, "kept": 1, "reused": 1})

    def test_only_generated_entries_render(self):
        saved = ip.ICONS
        try:
            ip.ICONS = gi.ICONS = {"technology": {
                "new": {"subject": "a brass gear", "seed": None},
                "chosen": {"subject": "a brass gear", "seed": 1},
                "kept": {"subject": "a brass gear", "seed": ip.KEEP},
                "reuses": {"use": "gfx/interface/icons/invention_icons/radio.dds"},
            }}
            self.assertEqual(sorted(gi.generated("technology", set())), ["chosen", "new"])
            self.assertEqual([k for k, e in ip.ICONS["technology"].items()
                              if "use" not in e and gi.accepted(e)], ["chosen"])
        finally:
            ip.ICONS = gi.ICONS = saved


class WriteDecisionTests(unittest.TestCase):
    def test_changed_pick_is_rewritten_unknown_history_is_trusted(self):
        want = [1, "prompt b"]
        self.assertTrue(gi.needs_write(False, None, want))            # no DDS yet
        self.assertFalse(gi.needs_write(True, None, want))            # no record: trust it
        self.assertFalse(gi.needs_write(True, [1, "prompt b"], want))  # same pick
        self.assertTrue(gi.needs_write(True, [0, "prompt b"], want))   # seed changed
        self.assertTrue(gi.needs_write(True, [1, "prompt a"], want))   # subject changed


class LensCopyTests(unittest.TestCase):
    def test_shown_actions_get_a_byte_copy_hidden_ones_do_not(self):
        root = Path(tempfile.mkdtemp())
        d = root / "common" / "diplomatic_actions"
        d.mkdir(parents=True)
        (d / "a.txt").write_bytes(b"\xef\xbb\xbf" + (
            "shown = {\n\tgroups = { general }\n}\n"
            "hidden = {\n\tshow_in_lens = no # comment\n\tpact = { show_in_lens = no }\n}\n"
            "nested_only = {\n\tpact = {\n\t\tshow_in_lens = no\n\t}\n}\n").encode("utf-8"))
        icons = root / "gfx" / "interface" / "icons" / "diplomatic_action_icons"
        icons.mkdir(parents=True)
        for k in ("shown", "hidden", "nested_only"):
            (icons / f"{k}.dds").write_bytes(f"DDS {k}".encode())
        lens = root / "gfx" / "interface" / "icons" / "lens_toolbar_icons"
        lens.mkdir(parents=True)
        (lens / "shown.dds").write_bytes(b"placeholder")
        saved = ip.ICONS
        try:
            ip.ICONS = gi.ICONS = {"diplomatic_action": {
                k: {"subject": "x", "seed": 0} for k in ("shown", "hidden", "nested_only")}}
            self.assertEqual(gi.hidden_from_lens("diplomatic_action", root), {"hidden"})
            self.assertEqual(sorted(gi.sync_lens_copies("diplomatic_action", set(), root)),
                             ["nested_only", "shown"])
            self.assertEqual((lens / "shown.dds").read_bytes(), b"DDS shown")
            self.assertFalse((lens / "hidden.dds").exists())
            self.assertEqual(gi.sync_lens_copies("diplomatic_action", set(), root), [])
        finally:
            ip.ICONS = gi.ICONS = saved


FIXTURE = (
    "# techs\n"
    "alpha = {\n"
    "\tera = era_6\n"
    '\ttexture = "gfx/interface/icons/invention_icons/mass_communication.dds" # kept comment\n'
    "\tmodifier = {\n"
    '\t\ttexture = "not/the/icon.dds"\n'
    "\t}\n"
    "}\n"
    "beta = {\n"
    '\ttexture = "gfx/interface/icons/invention_icons/mass_communication.dds" # Placeholder Icon\n'
    "}\n"
    "gamma = { # braces in a comment { }\n"
    '\tdesc = "a { brace in a string"\n'
    '\ttexture = "gfx/interface/icons/invention_icons/radio.dds"\n'
    "}\n"
)


class RewriteTests(unittest.TestCase):
    def _file(self, text: str = FIXTURE) -> Path:
        p = Path(tempfile.mkdtemp()) / "techs.txt"
        p.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        return p

    def test_only_the_named_icon_line_changes(self):
        p = self._file()
        changed = gi.rewrite_icon_refs(p, "texture", {"alpha": "gfx/new/alpha.dds",
                                                      "gamma": "gfx/new/gamma.dds"})
        self.assertEqual(changed, ["alpha", "gamma"])
        raw = p.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        # alpha's depth-1 line keeps its comment; its nested texture, beta and
        # everything else stay as they were.
        expected = (FIXTURE
                    .replace('\ttexture = "gfx/interface/icons/invention_icons/mass_communication.dds"'
                             ' # kept comment\n', '\ttexture = "gfx/new/alpha.dds" # kept comment\n')
                    .replace('"gfx/interface/icons/invention_icons/radio.dds"', '"gfx/new/gamma.dds"'))
        self.assertEqual(raw[3:].decode("utf-8"), expected)

    def test_placeholder_comment_is_dropped(self):
        p = self._file()
        gi.rewrite_icon_refs(p, "texture", {"beta": "gfx/new/beta.dds"})
        self.assertIn(b'beta = {\n\ttexture = "gfx/new/beta.dds"\n}', p.read_bytes())

    def test_missing_icon_line_is_inserted_first_in_the_block(self):
        text = ("acted = {\n\tgroups = { general }\n\tpact = {\n\t\ttexture = \"not/this.dds\"\n\t}\n}\n"
                "other = {\n\tgroups = { general }\n}\n")
        p = self._file(text)
        self.assertEqual(gi.rewrite_icon_refs(p, "texture", {"acted": "gfx/a.dds"}), ["acted"])
        self.assertEqual(p.read_bytes()[3:].decode("utf-8"),
                         text.replace("acted = {\n", 'acted = {\n\ttexture = "gfx/a.dds"\n'))
        self.assertEqual(gi.rewrite_icon_refs(p, "texture", {"acted": "gfx/a.dds"}), [])

    def test_rewrite_is_idempotent(self):
        p = self._file()
        gi.rewrite_icon_refs(p, "texture", {"beta": "gfx/new/beta.dds"})
        after = p.read_bytes()
        self.assertEqual(gi.rewrite_icon_refs(p, "texture", {"beta": "gfx/new/beta.dds"}), [])
        self.assertEqual(p.read_bytes(), after)

    def test_dry_run_writes_nothing(self):
        p = self._file()
        before = p.read_bytes()
        self.assertEqual(gi.rewrite_icon_refs(p, "texture", {"beta": "x.dds"}, dry_run=True), ["beta"])
        self.assertEqual(p.read_bytes(), before)

    def test_current_icons_reads_depth_one_only(self):
        root = Path(tempfile.mkdtemp())
        d = root / "common" / "technology" / "technologies"
        d.mkdir(parents=True)
        (d / "t.txt").write_bytes(b"\xef\xbb\xbf" + FIXTURE.encode("utf-8"))
        self.assertEqual(gi.current_icons("technology", root), {
            "alpha": "gfx/interface/icons/invention_icons/mass_communication.dds",
            "beta": "gfx/interface/icons/invention_icons/mass_communication.dds",
            "gamma": "gfx/interface/icons/invention_icons/radio.dds",
        })


@unittest.skipIf(icon_dds is None, "Pillow is not installed")
class DdsWriterTests(unittest.TestCase):
    def test_header_matches_vanilla_invention_icon(self):
        # mass_communication.dds's header with its NVTT signature (reserved
        # words 9 and 10) zeroed.
        vanilla = struct.pack(
            "<4s7I11I2I4s5I4I I",
            b"DDS ", 124, 0x2100F, 256, 256, 1024, 0, 9, *([0] * 11),
            32, 0x41, b"\0\0\0\0", 32, 0xFF0000, 0xFF00, 0xFF, 0xFF000000,
            0x401008, 0, 0, 0, 0)
        self.assertEqual(icon_dds.header(256, 256, 9), vanilla)

    def test_file_layout_and_round_trip(self):
        rng = np.random.default_rng(0)
        src = Image.fromarray(rng.integers(0, 256, (100, 100, 4), dtype=np.uint8), "RGBA")
        p = Path(tempfile.mkdtemp()) / "x.dds"
        icon_dds.write_dds(src, p)
        data = p.read_bytes()
        sizes = icon_dds.mip_sizes(100, 100)
        self.assertEqual(len(sizes), 7)  # vanilla's 100² icons carry 7 levels
        self.assertEqual(len(data), 128 + sum(w * h * 4 for w, h in sizes))
        back = Image.open(p)
        back.load()
        self.assertEqual(np.asarray(back.convert("RGBA")).tolist(), np.asarray(src).tolist())

    def test_mip_counts_match_vanilla_folders(self):
        self.assertEqual([len(icon_dds.mip_sizes(n, n)) for n in (256, 220, 208, 158, 100)],
                         [9, 8, 8, 8, 7])


if __name__ == "__main__":
    unittest.main()
