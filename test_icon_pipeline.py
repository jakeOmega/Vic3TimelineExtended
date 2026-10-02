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
            if "gui" in ip.CATEGORIES[cat]:
                continue                                    # GUI-hosted: entries name their placeholder
            self.assertIn("entity_dir", ip.CATEGORIES[cat])
            self.assertIn("field", ip.CATEGORIES[cat])

    def test_check_gui_hosted_parts_and_derived_entries(self):
        gi_ = "gfx/interface/icons/generic_icons"
        saved = ip.ICONS
        try:
            ip.ICONS = {
                "un_part": {"emblem": {"subject": "a laurel", "seed": 0},       # accepted part: no DDS needed
                            "badge": {"subject": "a scroll", "seed": None}},
                "un_disc": {
                    "agency_a": {"subject": "an anchor", "seed": 1, "now": f"{gi_}/x.dds"},
                    "no_now": {"subject": "an anchor", "seed": None},
                    "topic_a": {"from": "un_disc/agency_a", "marks": [{"part": "un_part/badge"}],
                                "now": f"{gi_}/x.dds"},                      # badge unpicked: not yet due
                    "bad_from": {"from": "un_disc/nowhere", "now": f"{gi_}/x.dds"},
                    "from_derived": {"from": "un_disc/topic_a", "now": f"{gi_}/x.dds"},
                    "bad_mark": {"subject": "a sword", "seed": None, "now": f"{gi_}/x.dds",
                                 "marks": [{"icon": f"{gi_}/red_cross.dds", "draw": "star"}]},
                    "part_not_a_part": {"from": "un_disc/agency_a", "now": f"{gi_}/x.dds",
                                        "marks": [{"part": "un_disc/agency_a"}]},
                },
                "un_member": {
                    "member": {"from": "un_part/emblem", "marks": [{"draw": "star", "at": (0.2, 0.2)}],
                               "now": f"{gi_}/x.dds"},                       # due: emblem accepted
                    "bad_tint": {"from": "un_part/emblem", "tint": "sepia", "now": f"{gi_}/x.dds"},
                    "flag_no_size": {"from": "un_part/emblem", "layout": "flag", "now": f"{gi_}/x.dds"},
                },
            }
            r = ip.check(tempfile.mkdtemp(), on_disk=set())
        finally:
            ip.ICONS = saved
        self.assertEqual(r["unknown"], [])                                   # no entity files to miss
        self.assertEqual(sorted(r["bad_entry"]), [
            ("un_disc", "bad_from"), ("un_disc", "bad_mark"), ("un_disc", "from_derived"),
            ("un_disc", "no_now"), ("un_disc", "part_not_a_part"),
            ("un_member", "bad_tint"), ("un_member", "flag_no_size")])
        self.assertEqual(sorted(r["missing_dds"]), [("un_disc", "agency_a"), ("un_member", "member")])
        self.assertEqual(r["states"]["un_disc"]["derived"], 1)

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
                         {"unreviewed": 2, "accepted": 1, "kept": 1, "reused": 1, "derived": 0})

    def test_check_knows_replace_or_create_definitions(self):
        saved = ip.ICONS
        try:
            ip.ICONS = {"building": {k: {"subject": "a mine", "seed": None} for k in
                                     ("building_lithium_mine", "building_iron_mine")}}
            d = tempfile.mkdtemp()
            bdir = Path(d) / "common" / "buildings"
            bdir.mkdir(parents=True)
            (bdir / "b.txt").write_text(
                "REPLACE_OR_CREATE:building_lithium_mine = {\n}\nREPLACE:building_iron_mine = {\n}\n",
                encoding="utf-8-sig")
            r = ip.check(d, on_disk=set())
        finally:
            ip.ICONS = saved
        self.assertEqual(r["unknown"], [("building", "building_iron_mine")])

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
            ip.ICONS = gi.ICONS = {"un_disc": {
                "agency": {"subject": "an anchor", "seed": 0, "now": "gfx/x.dds"},
                "topic": {"from": "un_disc/agency", "now": "gfx/x.dds"},
            }}
            self.assertEqual(list(gi.generated("un_disc", set())), ["agency"])   # derived: never rendered
            self.assertEqual(list(gi.derived("un_disc", set())), ["topic"])
            self.assertFalse(gi.accepted(ip.ICONS["un_disc"]["topic"]))
            self.assertTrue(gi.derived_ready(ip.ICONS["un_disc"]["topic"]))
        finally:
            ip.ICONS = gi.ICONS = saved


    def test_check_flags_a_bad_backdrop(self):
        saved_icons, saved_bd = ip.ICONS, ip.CATEGORIES["journal_entry_space"]["backdrop"]
        d = tempfile.mkdtemp()
        jdir = Path(d) / "common" / "journal_entries"
        jdir.mkdir(parents=True)
        (jdir / "j.txt").write_text("je_a = {\n}\n", encoding="utf-8-sig")

        def flagged(backdrop, seed):
            ip.ICONS = {"journal_entry_space": {"je_a": {"subject": "a silver sphere", "seed": seed}}}
            ip.CATEGORIES["journal_entry_space"]["backdrop"] = backdrop
            return ip.check(d, on_disk={ip.icon_path("journal_entry_space", "je_a")})["bad_backdrop"]

        try:
            ok = dict(seed=None, seeds=4, prompt="a night sky")
            self.assertEqual(flagged(ok, None), [])                          # still under review
            self.assertEqual(flagged(dict(ok, seed=2), 1), [])               # picked, icon accepted
            self.assertEqual(flagged(dict(ok, prompt=""), None), [("journal_entry_space", "_backdrop")])
            self.assertEqual(flagged(dict(ok, seed="2"), None), [("journal_entry_space", "_backdrop")])
            self.assertEqual(flagged(ok, 1), [("journal_entry_space", "_backdrop")])  # icon over an unpicked backdrop
        finally:
            ip.ICONS = saved_icons
            ip.CATEGORIES["journal_entry_space"]["backdrop"] = saved_bd

    def test_journal_categories_cover_every_mod_entry_but_the_nuclear_one(self):
        """Every mod-defined journal entry is in the registry, except the nuclear one (own art).
        REPLACE:-ed vanilla entries do not match the pattern, and the registry cannot wire them."""
        import re
        defined = set()
        for path in Path(MOD_ROOT, "common", "journal_entries").glob("*.txt"):
            defined |= set(re.findall(r"^([A-Za-z0-9_]+)\s*=\s*\{", path.read_text(encoding="utf-8-sig"), re.M))
        registered = set(ip.ICONS["journal_entry"]) | set(ip.ICONS["journal_entry_space"])
        self.assertEqual(defined - registered, {"je_nuclear_program"})
        self.assertEqual(registered - defined, set())


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

    def test_replace_or_create_is_matched_by_its_bare_key(self):
        # Mod-added buildings are often REPLACE_OR_CREATE:; REPLACE: and INJECT:
        # change a vanilla entity, whose own art stays.
        text = ('REPLACE_OR_CREATE:building_lithium_mine = {\n\ticon = "gfx/old/gold_mine.dds"\n}\n'
                'REPLACE:building_iron_mine = {\n\ticon = "gfx/old/iron_mine.dds"\n}\n'
                'INJECT:building_gold_mine = {\n\ticon = "gfx/old/gold_mine.dds"\n}\n')
        p = self._file(text)
        targets = {k: f"gfx/new/{k}.dds" for k in
                   ("building_lithium_mine", "building_iron_mine", "building_gold_mine")}
        self.assertEqual(gi.rewrite_icon_refs(p, "icon", targets), ["building_lithium_mine"])
        self.assertEqual(p.read_bytes()[3:].decode("utf-8"),
                         text.replace("gfx/old/gold_mine.dds", "gfx/new/building_lithium_mine.dds", 1))

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


@unittest.skipIf(icon_dds is None, "Pillow is not installed")
class EmbossGradientTests(unittest.TestCase):
    """`color_bottom` shades the emboss from `color` at the shape's top to it at its bottom."""

    def setUp(self):
        try:
            import scipy  # noqa: F401  (gen_pm_icons' outline)
        except ImportError:
            self.skipTest("scipy is not installed")
        import icon_render
        self.embossed = icon_render.embossed
        raw = np.full((256, 256, 3), 255, np.uint8)
        raw[40:216, 70:186] = 0  # a black upright bar on white
        self.raw = Image.fromarray(raw)
        self.spec = {"fill": 0.86, "color": (200, 120, 80)}

    def test_one_colour_is_unchanged(self):
        plain = np.asarray(self.embossed(self.raw, self.spec, 64))
        same = np.asarray(self.embossed(self.raw, dict(self.spec, color_bottom=self.spec["color"]), 64))
        self.assertLessEqual(np.abs(plain.astype(int) - same).max(), 1)

    def test_top_takes_color_bottom_takes_color_bottom(self):
        a = np.asarray(self.embossed(self.raw, dict(self.spec, color=(200, 200, 200), color_bottom=(200, 50, 50)), 64))
        rows = np.nonzero((a[..., 3] > 200).any(axis=1))[0]
        cols = slice(28, 36)  # the middle of the bar, clear of the bevel
        top, bottom = a[rows[0] + 6, cols, :3].mean(0), a[rows[-1] - 6, cols, :3].mean(0)
        self.assertGreater(top[1] / top[0], 0.8)     # grey at the top
        self.assertLess(bottom[1] / bottom[0], 0.4)  # red at the bottom
        self.assertTrue((a[..., 3] == np.asarray(self.embossed(self.raw, self.spec, 64))[..., 3]).all())


@unittest.skipIf(icon_dds is None, "Pillow is not installed")
class SpreadGradeAndRecolorTests(unittest.TestCase):
    """`grade_spread` moves two percentiles; `recolor_card`/`recolor_rgb` turn a card's hue."""

    NO_DISC = ((-1000, -1000, -1000),)  # every opaque pixel counts as object

    def setUp(self):
        import icon_render
        self.r = icon_render

    def _hsv_image(self, h, s, v):
        hsv = np.stack(np.broadcast_arrays(h, s, v), axis=-1) * 255
        im = Image.fromarray(np.clip(hsv + 0.5, 0, 255).astype(np.uint8), "HSV").convert("RGBA")
        return im

    def _pct(self, im, ch):
        hsv = np.asarray(im.convert("RGB").convert("HSV"), dtype=np.float32) / 255
        return np.percentile(hsv[..., ch], (50, 90))

    def test_moves_both_percentiles_and_keeps_order(self):
        v = np.linspace(0.9, 1.0, 64 * 64).reshape(64, 64)  # bright and flat
        im = self._hsv_image(30 / 360, 0.5, v)
        out = self.r.grade_spread(im, {2: np.array([0.6, 0.8])}, self.NO_DISC, strength=1.0)
        np.testing.assert_allclose(self._pct(out, 2), [0.6, 0.8], atol=0.03)
        before = np.asarray(im.convert("RGB").convert("HSV"))[..., 2].ravel()
        after = np.asarray(out.convert("RGB").convert("HSV"))[..., 2].ravel()
        self.assertTrue((np.diff(after[np.argsort(before, kind="stable")].astype(int)) >= 0).all())
        self.assertTrue((np.asarray(out)[..., 3] == 255).all())

    def test_saturation_gain_is_capped(self):
        s = np.linspace(0.01, 0.04, 64 * 64).reshape(64, 64)  # near grey
        im = self._hsv_image(200 / 360, s, 0.6)
        out = self.r.grade_spread(im, {1: np.array([0.4, 0.6])}, self.NO_DISC, strength=1.0, max_gain=1.6)
        self.assertLess(self._pct(out, 1)[0], self._pct(im, 1)[0] * 1.6 + 0.01)

    def test_recolor_turns_hue_and_keeps_value(self):
        pink = (184, 129, 128)
        gold = self.r.recolor_rgb(pink, 45, 1.0)
        import colorsys
        h0, s0, v0 = colorsys.rgb_to_hsv(*(c / 255 for c in pink))
        h1, s1, v1 = colorsys.rgb_to_hsv(*(c / 255 for c in gold))
        self.assertAlmostEqual((h1 - h0) % 1, 45 / 360, places=3)
        self.assertAlmostEqual(v1, v0, places=3)
        card = np.zeros((8, 8, 4), np.float32)
        card[..., :3] = pink
        card[..., 3] = 200
        turned = self.r.recolor_card(card, 45, 1.0)
        self.assertLess(np.abs(turned[0, 0, :3] - gold).max(), 4)  # PIL's 8-bit hue
        self.assertTrue((turned[..., 3] == 200).all())


@unittest.skipIf(icon_dds is None, "Pillow is not installed")
class StripTests(unittest.TestCase):
    """compose_strip centres the scene on a 3500x220 strip; icon_path honours `root`."""

    def setUp(self):
        try:
            import scipy  # noqa: F401  (the sides' blur)
        except ImportError:
            self.skipTest("scipy is not installed")
        import icon_render
        self.r = icon_render

    def test_scene_sits_sharp_in_the_middle(self):
        rng = np.random.default_rng(0)
        raw = Image.fromarray(rng.integers(40, 200, (448, 1792, 3), dtype=np.uint8))
        target = {1: np.array([0.4, 0.6]), 2: np.array([0.5, 0.7])}
        strip = np.asarray(self.r.compose_strip(raw, {"size": (3500, 220)}, target)).astype(float)
        self.assertEqual(strip.shape, (220, 3500, 4))
        self.assertTrue((strip[..., 3] == 255).all())
        detail = np.abs(np.diff(strip[..., :3].mean(-1), axis=1)).mean(0)  # horizontal texture per column
        x0 = self.r.STRIP_CENTRE - 440
        self.assertGreater(detail[x0 + 100:x0 + 780].mean(), 5 * detail[:600].mean())  # sides blurred
        self.assertLess(strip[:, :300, :3].mean(), strip[:, x0:x0 + 880, :3].mean())  # and dimmed

    def test_icon_path_takes_the_category_root(self):
        self.assertEqual(ip.icon_path("institution_strip", "institution_ministry_of_war"),
                         "gfx/interface/illustrations/institutions/institution_ministry_of_war.dds")
        self.assertEqual(ip.icon_path("institution", "institution_ministry_of_war"),
                         "gfx/interface/icons/institution_icons/institution_ministry_of_war.dds")


class BackdropPlumbingTests(unittest.TestCase):
    """The backed category's shared backdrop: which jobs render, where finals go, when writing is refused."""

    def setUp(self):
        self.cat = "journal_entry_space"
        self.spec = ip.CATEGORIES[self.cat]
        self.saved_seed = self.spec["backdrop"]["seed"]

    def tearDown(self):
        self.spec["backdrop"]["seed"] = self.saved_seed

    def test_backdrop_seed_and_final_dir_follow_the_pick(self):
        work = Path("/w")
        self.spec["backdrop"]["seed"] = None
        self.assertEqual(gi.backdrop_seed(self.cat), 0)               # candidates go over s0 in review
        self.assertEqual(gi.final_dir(self.cat, work), work / "final" / f"{self.cat}_bd0")
        self.spec["backdrop"]["seed"] = 3
        self.assertEqual(gi.final_dir(self.cat, work), work / "final" / f"{self.cat}_bd3")
        self.assertEqual(gi.final_dir("technology", work), work / "final")  # no backdrop, no subfolder

    def test_write_is_refused_until_the_backdrop_is_picked(self):
        saved = ip.ICONS
        try:
            ip.ICONS = gi.ICONS = {self.cat: {"je_x": {"subject": "a silver sphere", "seed": 0}}}
            self.spec["backdrop"]["seed"] = None
            with self.assertRaisesRegex(SystemExit, "pick the backdrop"):
                gi.stage_write(self.cat, set(), Path(tempfile.mkdtemp()))
        finally:
            ip.ICONS = gi.ICONS = saved

    @unittest.skipIf(icon_dds is None, "Pillow is not installed")
    def test_render_jobs_include_the_backdrop_only_when_asked_for(self):
        import icon_render
        saved, saved_embed, saved_render = ip.ICONS, icon_render.embed, icon_render.render
        jobs_seen = []
        try:
            ip.ICONS = gi.ICONS = {self.cat: {"je_a": {"subject": "a silver sphere", "seed": None},
                                              "je_b": {"subject": "a gold lander", "seed": None}}}
            icon_render.embed = lambda prompts, emb_dir: None
            icon_render.render = lambda jobs, *a, **k: jobs_seen.append(list(jobs))

            def names(only):
                jobs_seen.clear()
                gi.stage_render(self.cat, only, Path("/w"), 2, "sequential")
                return [(n.split("__", 1)[1], s) for n, _, s in jobs_seen[0]]

            self.spec["backdrop"]["seed"] = None
            everything = names(set())
            self.assertEqual([j for j in everything if j[0] == gi.BACKDROP],
                             [(gi.BACKDROP, s) for s in range(self.spec["backdrop"]["seeds"])])
            self.assertEqual(len([j for j in everything if j[0] != gi.BACKDROP]), 4)  # 2 subjects x 2 seeds
            self.assertEqual({j[0] for j in names({"je_a"})}, {"je_a"})               # not for a subject rerun
            self.assertEqual({j[0] for j in names({gi.BACKDROP})}, {gi.BACKDROP})     # alone, picked first
            self.spec["backdrop"]["seed"] = 2
            self.assertEqual(names({gi.BACKDROP}), [(gi.BACKDROP, 2)])               # picked: its seed only
        finally:
            ip.ICONS = gi.ICONS = saved
            icon_render.embed, icon_render.render = saved_embed, saved_render


@unittest.skipIf(icon_dds is None, "Pillow is not installed")
class BackedComposeTests(unittest.TestCase):
    """compose_backdrop makes a soft-edged, vignetted disc; compose_backed lays a subject over it."""

    SIZE = 150

    def setUp(self):
        import icon_render
        self.r = icon_render
        self.spec = dict(size=self.SIZE, fill=0.5, disc_fill=0.86)
        self.flat = Image.new("RGB", (256, 256), (60, 80, 140))

    def test_backdrop_is_a_disc_inside_the_frames_ring(self):
        disc = np.asarray(self.r.compose_backdrop(self.flat, self.spec)).astype(float)
        c = self.SIZE // 2
        self.assertEqual(disc[c, c, 3], 255)
        self.assertEqual(disc[0, 0, 3], 0)                            # corners stay clear of the round frame
        edge = int(c + self.SIZE * 0.86 / 2)
        self.assertGreater(disc[c, edge - 3, 3], 200)
        self.assertLess(disc[c, min(edge + 3, self.SIZE - 1), 3], 40)

    def test_vignette_darkens_the_rim_only(self):
        disc = np.asarray(self.r.compose_backdrop(self.flat, dict(self.spec, rim=0))).astype(float)
        c = self.SIZE // 2
        centre = disc[c, c, :3].sum()
        self.assertAlmostEqual(disc[c, c + 20, :3].sum(), centre, delta=2)   # inside 0.55 of the radius
        self.assertLess(disc[c, c + 60, :3].sum(), centre * 0.85)

    def test_subject_sits_over_the_disc_and_the_disc_survives_around_it(self):
        raw = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        raw.paste((200, 30, 30, 255), (16, 16, 48, 48))
        saved = self.r.cut_out
        self.r.cut_out = lambda im: im                                  # rembg is a GPU-venv dependency
        try:
            disc = self.r.compose_backdrop(self.flat, self.spec)
            icon = self.r.compose_backed(raw, self.spec, (0.45, 0.57), disc)
        finally:
            self.r.cut_out = saved
        a, b = np.asarray(icon).astype(int), np.asarray(disc).astype(int)
        c = self.SIZE // 2
        self.assertEqual(icon.size, (self.SIZE, self.SIZE))
        self.assertGreater(a[c, c, 0], a[c, c, 2] + 60)                 # the red subject is on top
        self.assertTrue((a[..., 3] == b[..., 3]).all())                # the disc's outline is unchanged
        far = (c, int(self.SIZE * 0.2))
        self.assertTrue((a[far] == b[far]).all())                       # away from the subject: bare disc

    def test_backed_needs_its_backdrop(self):
        composer = self.r.Composer()
        composer._target["journal_entry_space"] = (0.45, 0.57)          # skip reading vanilla's icons
        with self.assertRaises(ValueError):
            composer.compose(Image.new("RGB", (8, 8)), "journal_entry_space", ip.CATEGORIES["journal_entry_space"])


@unittest.skipIf(icon_dds is None, "Pillow is not installed")
class DerivedIconTests(unittest.TestCase):
    """The UN's derived icons: a drawn disc, tints, marks over an icon, the flag layout, and writing them."""

    def setUp(self):
        import icon_render
        self.r = icon_render

    def test_drawn_disc_is_blue_enamel_under_a_gold_rim(self):
        drawn = ip.CATEGORIES["un_disc"]["backdrop"]["drawn"]
        disc = np.asarray(self.r.draw_disc(150, drawn)).astype(int)
        self.assertEqual(disc[0, 0, 3], 0)                                    # round, not square
        self.assertEqual(disc[75, 75, 3], 255)
        r, g, b = disc[75, 75, :3]
        self.assertGreater(b, r + 40)                                         # enamel: blue
        r, g, b = disc[8, 75, :3]                                             # top of the rim
        self.assertGreater(r, b + 40)                                         # rim: gold

    def test_tints(self):
        im = Image.new("RGBA", (8, 8), (200, 40, 40, 255))
        grey = np.asarray(self.r.tint(im, "grey")).astype(int)
        self.assertLess(np.ptp(grey[0, 0, :3]), 20)                           # colour gone
        self.assertEqual(grey[0, 0, 3], 255)
        self.assertLess(np.asarray(self.r.tint(im, "faint"))[0, 0, 3], 128)   # faded as well
        self.assertIs(self.r.tint(im, None), im)
        with self.assertRaises(ValueError):
            self.r.tint(im, "sepia")

    def test_marks_land_where_they_are_placed(self):
        base = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
        green = Image.new("RGBA", (40, 40), (20, 200, 20, 255))
        out = np.asarray(self.r.apply_marks(base, [{"icon": "x"}, {"draw": "star", "at": (0.24, 0.24), "scale": 0.4}],
                                            lambda m: green)).astype(int)
        self.assertGreater(out[108, 108, 1], 150)                             # default: lower right
        self.assertEqual(out[140, 20, 3], 0)                                  # lower left untouched
        self.assertGreater(out[36, 36, 0], 150)                               # the star, gold, top left
        self.assertEqual(np.asarray(base)[108, 108, 3], 0)                    # the input is not changed

    def test_solid_fills_the_holes_the_cut_out_left_inside_an_object(self):
        # A ring the cut-out left hollow: `solid` fills its middle from the raw render.
        try:
            import scipy  # noqa: F401  (icon_render.cut's binary_fill_holes)
        except ImportError:
            self.skipTest("scipy is not installed")
        raw = Image.new("RGB", (60, 60), (120, 80, 40))
        ring = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
        ring.paste((120, 80, 40, 255), (10, 10, 50, 50))
        ring.paste((0, 0, 0, 0), (20, 20, 40, 40))
        saved = self.r.cut_out
        self.r.cut_out = lambda im: ring                                  # rembg is a GPU-venv dependency
        try:
            hollow = np.asarray(self.r.cut(raw, {}))
            solid = np.asarray(self.r.cut(raw, {"solid": True}))
        finally:
            self.r.cut_out = saved
        self.assertEqual(hollow[30, 30, 3], 0)
        self.assertEqual(solid[30, 30, 3], 255)
        self.assertEqual(tuple(solid[30, 30, :3]), (120, 80, 40))         # the raw's colours
        self.assertEqual(solid[5, 5, 3], 0)                               # outside stays clear

    def test_flag_layout(self):
        emblem = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        emblem.paste((200, 160, 60, 255), (30, 30, 70, 70))
        flag = np.asarray(self.r.flag_layout(emblem, (132, 88))).astype(int)
        self.assertEqual(flag.shape, (88, 132, 4))
        self.assertTrue((flag[..., 3] == 255).all())                          # opaque cloth
        self.assertGreater(flag[44, 66, :3].sum(), flag[44, 10, :3].sum())    # the watermark is lighter
        self.assertLess(flag[0, 66, :3].sum(), flag[44, 10, :3].sum())        # a dark border

    def test_derived_icons_are_written_once_their_source_is_picked(self):
        import icon_render
        root, work = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        (root / "gfx" / "interface").mkdir(parents=True)
        saved = (ip.ICONS, gi.MOD_ROOT, icon_render.vanilla_icons_dir)
        emblem = {"subject": "a laurel", "seed": None}
        try:
            ip.ICONS = gi.ICONS = {"un_part": {"emblem": emblem},
                                   "un_member": {"member": {"from": "un_part/emblem", "tint": "grey",
                                                            "marks": [{"draw": "star"}], "now": "gfx/x.dds"}}}
            gi.MOD_ROOT = root
            icon_render.vanilla_icons_dir = lambda: root / "game" / "gfx" / "interface" / "icons"
            # A raw render and its composed final, newer than it, so nothing is recomposed.
            (work / "raw").mkdir()
            (work / "final").mkdir()
            Image.new("RGB", (64, 64), "white").save(work / "raw" / "un_part__emblem__s1.png")
            final = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
            final.paste((40, 90, 200, 255), (30, 30, 120, 120))
            final.save(work / "final" / "un_part__emblem__s1.png")
            dest = root / ip.icon_path("un_member", "member")
            gi.stage_write("un_member", set(), work)
            self.assertFalse(dest.exists())                                   # emblem not picked yet
            emblem["seed"] = 1
            gi.stage_write("un_part", set(), work)                            # parts are never written
            self.assertFalse((root / ip.icon_path("un_part", "emblem")).exists())
            gi.stage_write("un_member", set(), work)
            self.assertTrue(dest.exists())
            mtime = dest.stat().st_mtime_ns
            gi.stage_write("un_member", set(), work)
            self.assertEqual(dest.stat().st_mtime_ns, mtime)                  # unchanged: left alone
            ip.ICONS["un_member"]["member"]["tint"] = None
            gi.stage_write("un_member", set(), work)
            self.assertNotEqual(dest.stat().st_mtime_ns, mtime)               # recipe changed: rewritten
        finally:
            ip.ICONS, gi.MOD_ROOT, icon_render.vanilla_icons_dir = saved
            gi.ICONS = ip.ICONS


@unittest.skipIf(icon_dds is None, "Pillow is not installed")
class PanelStateTests(unittest.TestCase):
    """The system panels' states: metal tints, drawn marks, breaks, placement, drawn entries."""

    def setUp(self):
        import icon_render
        self.r = icon_render

    def _stone(self):
        im = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
        im.paste((90, 88, 84, 255), (10, 10, 50, 30))
        im.paste((190, 186, 180, 255), (10, 30, 50, 50))
        return im

    def test_metal_tints_keep_the_shape_and_change_the_metal(self):
        stone = self._stone()
        gold = np.asarray(self.r.tint(stone, "gold")).astype(int)
        silver = np.asarray(self.r.tint(stone, "silver")).astype(int)
        iron = np.asarray(self.r.tint(stone, "iron")).astype(int)
        self.assertTrue((gold[..., 3] == np.asarray(stone)[..., 3]).all())     # same silhouette
        self.assertGreater(gold[40, 30, 0], gold[40, 30, 2] + 60)              # gold: warm
        self.assertLess(np.ptp(silver[40, 30, :3]), 25)                        # silver: near neutral, a little cool
        self.assertLess(iron[40, 30, :3].sum(), silver[40, 30, :3].sum())      # iron: darker than silver
        self.assertGreater(gold[40, 30, :3].sum(), gold[20, 30, :3].sum())     # light and shade kept
        moss = np.asarray(self.r.tint(stone, "moss")).astype(int)
        self.assertGreater(moss[20, 30, 1], moss[20, 30, 2])                   # shadows go green

    def test_arrows_point_the_way_they_are_told(self):
        up = np.asarray(self.r.arrow(60, "up", "green")).astype(int)
        down = np.asarray(self.r.arrow(60, "down", "red")).astype(int)
        # The tip is narrow and the tail is the shaft's width: up, the narrow end is on top.
        rows = lambda a: [w for w in (a[..., 3] > 128).sum(axis=1) if w]  # noqa: E731
        self.assertLess(rows(up)[0], rows(up)[-1])
        self.assertGreater(rows(down)[0], rows(down)[-1])
        self.assertGreater(up[40, 30, 1], up[40, 30, 0])                       # green
        self.assertGreater(down[20, 30, 0], down[20, 30, 1])                   # red

    def test_chevrons_count(self):
        for n in (1, 2, 4):
            col = np.asarray(self.r.chevrons(120, n))[:, 60].astype(int)       # the middle column
            a = np.concatenate([[False], (col[:, 3] > 128) & (col[:, 0] > 120)])   # gold, not the dark outline
            bands = int(np.sum(a[1:] & ~a[:-1]))
            self.assertEqual(bands, n)

    def test_bubble_rim_and_thermometer_level(self):
        rim = np.asarray(self.r.bubble(100, "green")).astype(int)
        self.assertGreater(rim[50, 5, 1], rim[50, 5, 0] + 40)                  # the rim carries the colour
        self.assertLess(rim[50, 50, 3], 128)                                   # the film is clear
        def column_top(level):
            a = np.asarray(self.r.thermometer(120, level)).astype(int)
            red = (a[..., 0] > 180) & (a[..., 1] < 90) & (a[:, :, 3] > 200)
            return int(np.argmax(red[:, 60]))
        self.assertLess(column_top(0.8), column_top(0.2))                      # higher column, higher top

    def test_disc_shield_dome_and_link(self):
        d = np.asarray(self.r.disc(60, "green")).astype(int)
        self.assertEqual(d[0, 0, 3], 0)                                        # round
        self.assertGreater(d[40, 30, 1], d[40, 30, 0] + 40)                    # green enamel
        sh = np.asarray(self.r.shield_outline(60, "blue"))
        self.assertLess(sh[26, 30, 3], 30)                                     # open inside
        self.assertGreater(sh[5, 30, 3], 200)                                  # the rim at the top
        dm = np.asarray(self.r.dome(60))
        self.assertLess(dm[40, 30, 3], 128)                                    # clear, so the rocket shows
        whole = np.asarray(self.r.link(100, "gold", 0.1))
        broken = np.asarray(self.r.link(100, "gold", 0.1, "broken"))
        self.assertGreater((whole[..., 3] > 128).sum(), (broken[..., 3] > 128).sum())   # a gap in the broken tie
        right = np.asarray(self.r.arrow(60, "right", "red"))
        widths = [w for w in (right[..., 3] > 128).sum(axis=0) if w]
        self.assertLess(widths[-1], widths[0])                                 # the tip on the right

    def test_eyelid_shuts_or_half_opens(self):
        shut = np.asarray(self.r.eyelid(100)).astype(int)
        half = np.asarray(self.r.eyelid(100, 0.5)).astype(int)
        self.assertGreater(shut[62, 50, 3], 200)                               # the lid covers the lower eye
        self.assertLess(half[64, 50, 3], 60)                                   # half open: the lower eye shows
        self.assertGreater(half[34, 50, 3], 200)                               # while the lid covers the top
        self.assertEqual(shut[5, 50, 3], 0)                                    # nothing outside the eye

    def test_pre_marks_are_part_of_the_emblem(self):
        # A `pre` mark is drawn before the tint, so it takes the emblem's metal.
        finals = gi.Finals.__new__(gi.Finals)
        finals.load_mark = lambda m: None
        base = Image.new("RGBA", (100, 100), (150, 150, 150, 255))
        finals.get = lambda cat, key, seed: base
        e = {"from": "covert_part/shield", "tint": "gold",
             "marks": [{"draw": "bar", "colour": "white", "at": (0.5, 0.5), "scale": 0.8, "pre": True}]}
        out = np.asarray(finals.derived(e, 0)).astype(int)
        self.assertGreater(out[50, 50, 0], out[50, 50, 2] + 40)               # the white bar turned gold

    def test_turn_and_rotated_marks(self):
        tall = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        tall.paste((200, 200, 200, 255), (45, 5, 55, 95))
        lying = np.asarray(self.r.turn(tall, -90))
        self.assertEqual(lying.shape, (100, 100, 4))
        self.assertTrue((lying[50, 10:90, 3] > 128).all())                     # now across, not up
        self.assertTrue((lying[10, 45:55, 3] < 128).all())
        bar = Image.new("RGBA", (40, 8), (220, 20, 20, 255))
        out = np.asarray(self.r.apply_marks(Image.new("RGBA", (100, 100), (0, 0, 0, 0)),
                                            [{"icon": "x", "at": (0.5, 0.5), "scale": 0.6, "rotate": 90,
                                              "outline": False}], lambda m: bar))
        self.assertGreater(out[30, 50, 3], 128)                                # the bar stands upright
        self.assertEqual(out[50, 25, 3], 0)

    def test_damage_and_tilt(self):
        solid = Image.new("RGBA", (80, 80), (160, 160, 160, 255))
        crack = np.asarray(self.r.damage(solid, "crack")).astype(int)
        self.assertTrue((crack[..., 3] == 255).all())                          # a crack keeps the shape
        self.assertLess(crack[..., :3].sum(axis=2).min(), 200)                 # and draws a dark line
        split = np.asarray(self.r.damage(solid, "split"))
        self.assertTrue((split[5:75, 40:50, 3] < 128).any())                   # a gap opens down the middle
        self.assertTrue((split[20:70, 10:26, 3] > 128).all() and (split[20:70, 55:68, 3] > 128).all())   # both halves
        tilted = np.asarray(self.r.damage(Image.new("RGBA", (80, 80), (0, 0, 0, 0)).crop((0, 0, 80, 80)), None, 9))
        self.assertEqual(tilted.shape, (80, 80, 4))
        with self.assertRaises(ValueError):
            self.r.damage(solid, "shatter")

    def test_place_and_marks_under(self):
        big = Image.new("RGBA", (100, 100), (200, 30, 30, 255))
        placed = np.asarray(self.r.place(big, 0.4, (0.5, 0.8)))
        self.assertEqual(placed[80, 50, 3], 255)
        self.assertEqual(placed[30, 50, 3], 0)
        blue = Image.new("RGBA", (40, 40), (20, 20, 220, 255))
        over = np.asarray(self.r.apply_marks(big, [{"icon": "x", "at": (0.5, 0.5)}], lambda m: blue))
        under = np.asarray(self.r.apply_marks(big, [{"icon": "x", "at": (0.5, 0.5), "under": True}], lambda m: blue))
        self.assertGreater(over[50, 50, 2], 150)
        self.assertGreater(under[50, 50, 0], 150)                              # hidden beneath the icon
        edge = self.r.apply_marks(big, [{"draw": "bar", "at": (0.98, 0.98)}], None)   # clipped, not refused
        self.assertEqual(edge.size, (100, 100))

    def test_check_takes_drawn_entries_and_the_new_settings(self):
        disc = {"centre": (1, 2, 3), "edge": (1, 2, 3), "rim_light": (1, 2, 3), "rim_dark": (1, 2, 3)}
        now = "gfx/interface/icons/x.dds"
        saved = ip.ICONS
        try:
            ip.ICONS = {
                "gw_part": {"crate": {"subject": "a crate", "seed": 1}},
                "gw_state": {
                    "tier": {"disc": disc, "marks": [{"draw": "thermometer", "level": 0.4}], "now": now},
                    "member": {"from": "gw_part/crate", "tint": "iron", "damage": "split", "tilt": 5,
                               "base": {"scale": 0.8, "at": (0.5, 0.6)},
                               "marks": [{"draw": "arrow", "dir": "up", "colour": "green", "under": True}],
                               "now": now},
                    "bad_damage": {"from": "gw_part/crate", "damage": "shatter", "now": now},
                    "bad_colour": {"from": "gw_part/crate", "marks": [{"draw": "arrow", "colour": "mauve"}],
                                   "now": now},
                    "bad_disc": {"disc": {"centre": (1, 2, 3)}, "now": now},
                    "bad_base": {"from": "gw_part/crate", "base": {"scale": 1.5}, "now": now},
                },
            }
            r = ip.check(on_disk={ip.icon_path("gw_state", "tier"), ip.icon_path("gw_state", "member")})
        finally:
            ip.ICONS = saved
        self.assertEqual(sorted(r["bad_entry"]), [("gw_state", "bad_base"), ("gw_state", "bad_colour"),
                                                  ("gw_state", "bad_damage"), ("gw_state", "bad_disc")])
        self.assertEqual(r["missing_dds"], [])
        self.assertEqual(r["states"]["gw_state"]["derived"], 2)
        self.assertEqual(gi.depends_on({"disc": disc}), [])                    # a drawn entry waits on nothing

    def test_drawn_entry_is_written_at_once(self):
        import icon_render
        root, work = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        (root / "gfx" / "interface").mkdir(parents=True)
        disc = {"centre": (150, 205, 195), "edge": (60, 120, 115), "rim_light": (240, 225, 190),
                "rim_dark": (120, 95, 60)}
        saved = (ip.ICONS, gi.MOD_ROOT, icon_render.vanilla_icons_dir)
        try:
            ip.ICONS = gi.ICONS = {"gw_state": {"tier": {"disc": disc, "now": "gfx/x.dds",
                                                         "marks": [{"draw": "thermometer", "level": 0.2}]}}}
            gi.MOD_ROOT = root
            icon_render.vanilla_icons_dir = lambda: root / "game" / "gfx" / "interface" / "icons"
            gi.stage_write("gw_state", set(), work)
            self.assertTrue((root / ip.icon_path("gw_state", "tier")).exists())
        finally:
            ip.ICONS, gi.MOD_ROOT, icon_render.vanilla_icons_dir = saved
            gi.ICONS = ip.ICONS


class RestyleTests(unittest.TestCase):
    """A restyle entry refits an existing icon: validation, candidates, source lookup and preparation."""

    def test_check_validates_restyle_entries(self):
        src = "gfx/interface/icons/building_icons/old.dds"
        saved = ip.ICONS
        try:
            ip.ICONS = {"building": {
                "building_ok": {"restyle": src, "subject": "an airport", "seed": None},
                "building_picked": {"restyle": src, "subject": "an airport", "seed": 2, "crop": 0.15},
                "building_own_strengths": {"restyle": src, "subject": "an airport", "seed": 3,
                                           "strengths": [0.0, 0.375, 0.5, 0.5]},
                "building_bad_path": {"restyle": "old.dds", "subject": "an airport", "seed": None},
                "building_bad_crop": {"restyle": src, "subject": "an airport", "seed": None, "crop": 0.4},
                "building_past_last": {"restyle": src, "subject": "an airport", "seed": 9},
                "building_bad_strength": {"restyle": src, "subject": "an airport", "seed": None, "strengths": [1.0]},
            }}
            d = tempfile.mkdtemp()
            bdir = Path(d) / "common" / "buildings"
            bdir.mkdir(parents=True)
            (bdir / "b.txt").write_text("".join(f"{k} = {{\n}}\n" for k in ip.ICONS["building"]),
                                        encoding="utf-8-sig")
            r = ip.check(d, on_disk={ip.icon_path("building", "building_picked"),
                                     ip.icon_path("building", "building_own_strengths")})
        finally:
            ip.ICONS = saved
        self.assertEqual(sorted(k for _, k in r["bad_entry"]),
                         ["building_bad_crop", "building_bad_path", "building_bad_strength", "building_past_last"])
        self.assertEqual(r["missing_dds"], [])

    def test_candidates_are_the_strengths(self):
        bare = {"restyle": "gfx/interface/icons/building_icons/old.dds", "subject": "an airport", "seed": None}
        self.assertEqual(ip.restyle_strengths("building", bare), ip.CATEGORIES["building"]["restyle_strengths"])
        e = dict(bare, strengths=[0.0, 0.375, 0.5])                # an entry's own list wins
        self.assertEqual(ip.restyle_strengths("building", e), (0.0, 0.375, 0.5))
        self.assertEqual(gi.caption("building", e, 0), "s0 as is")
        self.assertEqual(gi.caption("building", e, 2), "s2 repaint 0.5")
        self.assertEqual(gi.caption("building", {"subject": "a mine", "seed": None}, 1), "s1")
        self.assertEqual(gi.restyle_settings("building", dict(e, crop=0.15), 1),
                         {"restyle": e["restyle"], "crop": 0.15, "strength": 0.375})
        self.assertEqual(gi.restyle_settings("building", bare, 0)["crop"], ip.RESTYLE_CROP)

    @unittest.skipIf(icon_dds is None, "Pillow is not installed")
    def test_prepare_crops_the_border_and_fills_transparent_corners(self):
        import icon_render
        from PIL import ImageDraw
        im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))                         # a circular badge:
        ImageDraw.Draw(im).ellipse((0, 0, 199, 199), fill=(200, 40, 40, 255),    # red picture,
                                   outline=(0, 0, 255, 255), width=4)            # blue rim of its own
        out = np.asarray(icon_render.prepare_restyle(im, 0.05, size=64))
        self.assertEqual(out.shape, (64, 64, 3))
        corner = out[:4, -4:].reshape(-1, 3).mean(0)
        self.assertGreater(corner[0], 150)          # the empty corner takes the picture's red, not black
        self.assertLess(out[:, :, 2].max(), 60)     # the rim is gone

    @unittest.skipIf(icon_dds is None, "Pillow is not installed")
    def test_strength_zero_keeps_the_source_without_the_model(self):
        import icon_render
        raw_dir = Path(tempfile.mkdtemp())
        source = Image.new("RGB", (32, 32), (10, 120, 30))
        icon_render.restyle([("building__x", "p", 0, source, 0.0, "note")], raw_dir / "e", raw_dir)
        out = raw_dir / "building__x__s0.png"
        self.assertEqual(Image.open(out).getpixel((5, 5)), (10, 120, 30))
        self.assertEqual(out.with_suffix(".prompt.txt").read_text(encoding="utf-8"), "note")

    @unittest.skipIf(icon_dds is None, "Pillow is not installed")
    def test_source_is_read_from_disk_head_or_before_its_deletion(self):
        import subprocess
        root = Path(tempfile.mkdtemp())

        def git(*args):
            subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)

        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        rel = "gfx/old.png"
        (root / "gfx").mkdir()
        Image.new("RGB", (8, 8), (1, 2, 3)).save(root / rel)
        git("add", rel)
        git("commit", "-qm", "add")
        self.assertEqual(gi.restyle_source(rel, root).convert("RGB").getpixel((0, 0)), (1, 2, 3))   # on disk
        (root / rel).unlink()
        self.assertEqual(gi.restyle_source(rel, root).convert("RGB").getpixel((0, 0)), (1, 2, 3))   # HEAD
        git("rm", "-q", "--cached", rel)
        git("commit", "-qm", "delete")
        self.assertEqual(gi.restyle_source(rel, root).convert("RGB").getpixel((0, 0)), (1, 2, 3))   # history
        with self.assertRaisesRegex(SystemExit, "neither on disk nor in git"):
            gi.restyle_source("gfx/never.png", root)

    def test_render_sends_restyle_entries_to_img2img(self):
        import icon_render
        saved = (ip.ICONS, icon_render.embed, icon_render.render, getattr(icon_render, "restyle"), gi.restyle_jobs)
        seen = {}
        try:
            ip.ICONS = gi.ICONS = {"building": {
                "building_new": {"subject": "a mine", "seed": None},
                "building_old": {"restyle": "gfx/interface/icons/building_icons/old.dds", "subject": "an airport",
                                 "seed": None, "strengths": [0.0, 0.375, 0.5]},
            }}
            icon_render.embed = lambda prompts, emb_dir: seen.setdefault("embedded", sorted(prompts))
            icon_render.render = lambda jobs, *a, **k: seen.setdefault("render", [(n, s) for n, _, s in jobs])
            gi.restyle_jobs = lambda cat, items: [(gi.name(cat, k), p, i, None, x, "")
                                                  for k, e, p in items
                                                  for i, x in enumerate(ip.restyle_strengths(cat, e))]
            icon_render.restyle = lambda jobs, *a, **k: seen.setdefault("restyle", [(n, s, x) for n, _, s, _, x, _ in jobs])
            gi.stage_render("building", set(), Path("/w"), 2, "sequential")
        finally:
            ip.ICONS, icon_render.embed, icon_render.render, icon_render.restyle, gi.restyle_jobs = saved
            gi.ICONS = ip.ICONS
        self.assertEqual(seen["embedded"], ["building__building_new", "building__building_old"])
        self.assertEqual(seen["render"], [("building__building_new", 0), ("building__building_new", 1)])
        self.assertEqual(seen["restyle"], [("building__building_old", 0, 0.0), ("building__building_old", 1, 0.375),
                                           ("building__building_old", 2, 0.5)])


if __name__ == "__main__":
    unittest.main()
