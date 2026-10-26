"""Unit tests for texture_reference_audit (#1156).

An asset path in mod script that names no file renders the missing-texture
placeholder and logs only when first drawn. #1155's
`timed_modifier_icons/modifier_military_negative.dds` is the shape that must
flag; paths in the mod's tracked `gfx/`, vanilla's three mounts and the
leading-slash form vanilla's parties use must not. The committed catalog must
give CI the same answer the live install gives a reload.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import event_context_audit
import path_constants
import texture_reference_audit as tra


def _tree(root: str, files: dict[str, str]) -> str:
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return root


ALIASES = """# comment = { }
base_alias = {
	video = "gfx/event_pictures/base.bk2"
	fallback = other_alias
}
other_alias = { video = "gfx/event_pictures/other.bk2" }
"""

INSTALL = {
    "game/gfx/interface/icons/a.dds": "",
    "game/gfx/interface/icons/Mixed_Case.dds": "",
    "game/gfx/event_pictures/base.bk2": "",
    "game/gfx/models/ship.mesh": "",
    "game/gfx/event_pictures/placeholder scene.bk2": "",
    "game/gfx/coat_of_arms/patterns/pattern_solid.tga": "",
    "game/gfx/coat_of_arms/colored_emblems/ce_solid.dds": "",
    "game/gfx/interface/icons/Shared.dds": "",
    "game/gfx/media_aliases/media_aliases.txt": ALIASES,
    "jomini/gfx/FX/jomini_thing.shader": "",
    "clausewitz/gfx/FX/pdxgui_default.shader": "",
    "clausewitz/gfx/editor_gui/default_icon.dds": "",
    "game/dlc/dlc001_pack/gfx/event_pictures/dlc_video.bk2": "",
    "game/dlc/dlc001_pack/gfx/interface/icons/a.dds": "",
    "game/dlc/dlc001_pack/gfx/media_aliases/dlc_aliases.txt": "dlc_alias = { video = \"x\" }\n",
    "launcher/launcher-settings.json": json.dumps({"rawVersion": "9.9.9"}),
}

MOD_FILES = {"gfx/interface/icons/te_mod_icon.dds", "gfx/interface/icons/TE_Upper.dds",
             "gfx/interface/icons/SHARED.dds"}


class _Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.install = _tree(os.path.join(self._tmp, "install"), INSTALL)
        self.mod = os.path.join(self._tmp, "mod")
        os.makedirs(self.mod)
        paths, aliases = tra.scan_install(self.install)
        self.index = tra.AssetIndex(paths, aliases, set(MOD_FILES), source="install")

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def run_audit(self, files: dict[str, str], index=None):
        _tree(self.mod, files)
        return tra.audit(mod_path=self.mod, index=index or self.index)

    def kinds(self, result):
        return [(f.file, f.line, f.kind) for f in result.flags]


class ResolutionTests(_Fixture):
    def test_mod_and_vanilla_paths_resolve(self):
        r = self.run_audit({"common/static_modifiers/m.txt": (
            'm = {\n'
            '\ticon = "gfx/interface/icons/te_mod_icon.dds"\n'
            '\ticon = gfx/interface/icons/a.dds\n'
            '}\n')})
        self.assertEqual(r.flags, [])
        self.assertEqual(r.resolved, {"mod": 1, "vanilla": 1})
        self.assertEqual(r.references_checked, 2)

    def test_engine_mounts_resolve(self):
        # The brief's game/gfx-only set would have flagged both of these.
        r = self.run_audit({"gui/x.gui": (
            'widget = {\n'
            '\teffectname = "gfx/FX/pdxgui_default.shader"\n'
            '\ttexture = "gfx/editor_gui/default_icon.dds"\n'
            '\teffect = "gfx/FX/jomini_thing.shader"\n'
            '}\n')})
        self.assertEqual(r.flags, [])
        self.assertEqual(r.resolved, {"vanilla": 3})

    def test_leading_slash_is_dropped(self):
        r = self.run_audit({"common/parties/p.txt":
                            'p = { icon = { default = "/gfx/interface/icons/a.dds" } }\n'})
        self.assertEqual(r.flags, [])

    def test_missing_path_flags(self):
        r = self.run_audit({"common/static_modifiers/m.txt": (
            'm = {\n'
            '\ticon = "gfx/interface/icons/timed_modifier_icons/modifier_military_negative.dds"\n'
            '}\n')})
        self.assertEqual(self.kinds(r), [("common/static_modifiers/m.txt", 2, "missing")])
        self.assertEqual(r.flags[0].key, "icon")
        self.assertEqual(r.failing, 1)

    def test_path_without_gfx_root_is_unrooted(self):
        r = self.run_audit({"events/e.txt": 'e.1 = { event_image = { texture = "interface/icons/a.dds" } }\n'})
        self.assertEqual([f.kind for f in r.flags], ["unrooted"])

    def test_planted_breakages_flag(self):
        # Each was skipped, not flagged, before the review (I2).
        r = self.run_audit({"common/static_modifiers/m.txt": (
            'm = {\n'
            '\ticon = "modifier_coins_negative.dds"\n'
            '\tvideo = "foo.bk2"\n'
            '\ticon = "gfx/interface/icons/a.dss"\n'
            '\ticon = "gfx/interface/icons/a"\n'
            '\ticon = "gfx\\interface\\icons\\a.dds"\n'
            '\ticon = "gfx\\interface\\icons\\nope.dds"\n'
            '}\n')})
        self.assertEqual([(f.line, f.kind) for f in r.flags], [
            (2, "unrooted"), (3, "unrooted"), (4, "unknown_extension"), (5, "unknown_extension"),
            (6, "backslash"), (7, "backslash")])
        self.assertEqual([(f.detail, f.fixed_status) for f in r.flags[4:]], [
            ("gfx/interface/icons/a.dds", "vanilla"), ("gfx/interface/icons/nope.dds", "missing")])
        self.assertIn("which resolves", tra.describe(r.flags[4]))
        self.assertIn("doesn't resolve either", tra.describe(r.flags[5]))
        self.assertEqual(r.failing, 6)

    def test_coat_of_arms_bare_names(self):
        r = self.run_audit({
            "common/coat_of_arms/coat_of_arms/c.txt": (
                'C = {\n'
                '\tpattern = "pattern_solid.tga"\n'
                '\tcolored_emblem = { texture = "ce_solid.dds" }\n'
                '\tcolored_emblem = { texture = "ce_nope.dds" }\n'
                '}\n'),
            "common/defines/d.txt": 'NGraphics = { PREVIEW_BACKGROUND_PATTERN = "pattern_solid.tga" }\n',
            "common/static_modifiers/m.txt": 'm = { icon = "ce_solid.dds" }\n',
        })
        self.assertEqual([(f.file, f.line, f.kind) for f in r.flags], [
            ("common/coat_of_arms/coat_of_arms/c.txt", 4, "missing"),
            ("common/static_modifiers/m.txt", 1, "unrooted")])
        self.assertEqual(r.resolved, {"vanilla": 3})

    def test_untracked_file_on_disk(self):
        _tree(self.mod, {"gfx/interface/icons/te_new.dds": ""})
        index, _ = tra.build_index(self.mod, source="install", base=self.install, mod_files=MOD_FILES)
        r = self.run_audit({"common/x.txt": 'a = "gfx/interface/icons/te_new.dds"\n'}, index)
        self.assertEqual([(f.kind, f.detail) for f in r.flags], [("missing", "untracked")])
        self.assertIn("git add", tra.describe(r.flags[0]))

    def test_mod_file_wins_the_case_fold(self):
        r = self.run_audit({"common/x.txt": 'a = "gfx/interface/icons/shared.dds"\n'})
        self.assertEqual([(f.kind, f.detail) for f in r.flags],
                         [("case_mismatch", "gfx/interface/icons/SHARED.dds")])

    def test_case_mismatch_is_an_error(self):
        r = self.run_audit({"common/x.txt": (
            'a = "gfx/interface/icons/mixed_case.dds"\n'
            'b = "gfx/interface/icons/te_upper.dds"\n')})
        self.assertEqual([(f.kind, f.detail) for f in r.flags], [
            ("case_mismatch", "gfx/interface/icons/Mixed_Case.dds"),
            ("case_mismatch", "gfx/interface/icons/TE_Upper.dds"),
        ])
        self.assertEqual(r.failing, 2)

    def test_dlc_only_warns_without_failing(self):
        r = self.run_audit({"events/e.txt": (
            'e.1 = {\n'
            '\tevent_image = { video = "gfx/event_pictures/dlc_video.bk2" }\n'
            '}\n')})
        self.assertEqual([(f.kind, f.detail) for f in r.flags], [("dlc_only", "dlc001_pack")])
        self.assertEqual(r.failing, 0)

    def test_path_in_base_and_dlc_is_vanilla(self):
        r = self.run_audit({"common/x.txt": 'a = "gfx/interface/icons/a.dds"\n'})
        self.assertEqual(r.flags, [])

    def test_explicit_dlc_path(self):
        r = self.run_audit({"common/themes/t.txt": (
            'a = "dlc/dlc001_pack/gfx/event_pictures/dlc_video.bk2"\n'
            'b = "dlc/dlc002_other/gfx/event_pictures/dlc_video.bk2"\n'
            'c = "dlc/DLC001_pack/gfx/event_pictures/dlc_video.bk2"\n')})
        self.assertEqual([(f.line, f.kind) for f in r.flags],
                         [(1, "dlc_only"), (2, "missing"), (3, "case_mismatch")])

    def test_media_aliases(self):
        r = self.run_audit({"events/e.txt": (
            'e.1 = {\n'
            '\tevent_image = { video = "base_alias" }\n'
            '\tevent_image = { video = other_alias }\n'
            '\tevent_image = { video = "no_such_alias" }\n'
            '\tevent_image = { video = "dlc_alias" }\n'
            '\tevent_image = { video = "$VIDEO$" }\n'
            '}\n')})
        self.assertEqual([(f.line, f.kind) for f in r.flags],
                         [(4, "unknown_media_alias"), (5, "dlc_only")])
        self.assertEqual(r.resolved, {"alias": 2})
        self.assertEqual([(s.line, s.kind) for s in r.skipped], [(6, "templated")])

    def test_mod_media_alias(self):
        _tree(self.mod, {"gfx/media_aliases/te_aliases.txt": "te_alias = { video = \"x\" }\n"})
        mod_files = set(MOD_FILES) | {"gfx/media_aliases/te_aliases.txt"}
        index, _ = tra.build_index(self.mod, source="install", base=self.install, mod_files=mod_files)
        r = self.run_audit({"events/e.txt": 'e.1 = { event_image = { video = "te_alias" } }\n'}, index)
        self.assertEqual(r.flags, [])
        self.assertEqual(r.resolved, {"alias": 1})


class ScanTests(_Fixture):
    def test_skipped_kinds(self):
        r = self.run_audit({"common/x.txt": (
            'a = "gfx/interface/icons/$ICON$.dds"\n'
            'b = "gfx/[GetIcon].dds"\n'
            'c = "gfx/models/ship.mesh"\n'
            'd = { video = $VIDEO$ }\n')})
        self.assertEqual(r.flags, [])
        self.assertEqual([(s.line, s.kind) for s in r.skipped],
                         [(1, "templated"), (2, "templated"), (3, "other_extension"), (4, "templated")])
        self.assertEqual(r.references_checked, 0)

    def test_display_text_is_not_a_path(self):
        r = self.run_audit({"gui/g.gui": (
            'w = {\n'
            '\traw_text = "flag_power_large.dds"\n'
            '\traw_text = "gfx/interface/nope.dds"\n'
            '\tdesc = "see the file nope.dds"\n'
            '}\n')})
        self.assertEqual(r.flags, [])
        self.assertEqual(r.references_checked, 0)

    def test_whitespace_in_and_around_paths(self):
        r = self.run_audit({"events/e.txt": (
            'e.1 = {\n'
            '\tevent_image = { video = "gfx/event_pictures/placeholder scene.bk2" }\n'
            '\ticon = "gfx/interface/icons/a.dds "\n'
            '\ticon = " gfx/interface/icons/nope.dds"\n'
            '}\n')})
        self.assertEqual([(f.line, f.kind, f.detail, f.fixed_status) for f in r.flags], [
            (3, "whitespace", "gfx/interface/icons/a.dds", "vanilla"),
            (4, "whitespace", "gfx/interface/icons/nope.dds", "missing")])
        self.assertEqual(r.resolved, {"vanilla": 1})

    def test_operators_keep_the_key(self):
        r = self.run_audit({"common/x.txt": (
            'a = { icon ?= "gfx/nope1.dds" }\n'
            'b = { icon?="gfx/nope2.dds" limit = { x >= 5 y != z } }\n')})
        self.assertEqual([(f.key, f.value) for f in r.flags],
                         [("icon", "gfx/nope1.dds"), ("icon", "gfx/nope2.dds")])

    def test_comments_text_and_quotes(self):
        r = self.run_audit({"common/x.txt": (
            '# icon = "gfx/nope_in_a_comment.dds"\n'
            'a = "#b gfx/nope.dds#!"  # trailing "gfx/nope_too.dds"\n'
            'raw_text = "see gfx/interface/nope.dds here"\n'
            'b = "gfx/nope_after#hash.dds"\n')})
        # Only the last, where the `#` sits inside the quoted path.
        self.assertEqual([(f.line, f.value) for f in r.flags], [(4, "gfx/nope_after#hash.dds")])

    def test_list_item_takes_its_block_name(self):
        r = self.run_audit({"common/x.txt": 'textures = { "gfx/nope1.dds" gfx/nope2.dds }\n'})
        self.assertEqual([(f.key, f.value) for f in r.flags],
                         [("textures", "gfx/nope1.dds"), ("textures", "gfx/nope2.dds")])

    def test_a_left_hand_side_is_not_a_value(self):
        r = self.run_audit({"common/x.txt": '"gfx/nope_lhs.dds" = { icon = "gfx/nope_rhs.dds" }\n'})
        self.assertEqual([(f.key, f.value) for f in r.flags], [("icon", "gfx/nope_rhs.dds")])

    def test_scanned_files(self):
        r = self.run_audit({
            "gui/a.gui": 'w = { texture = "gfx/nope_gui.dds" }\n',
            "gui/b.txt": 'w = { texture = "gfx/nope_gui_txt.dds" }\n',
            "common/eras/_eras.info": 'icon = "gfx/nope_info.dds"\n',
            "events/sub/e.txt": 'e.1 = { icon = "gfx/nope_event.dds" }\n',
            "localization/english/x_l_english.yml": 'l_english:\n k: "gfx/nope.dds"\n',
        })
        self.assertEqual(sorted(f.file for f in r.flags), ["events/sub/e.txt", "gui/a.gui"])
        self.assertEqual(r.files_audited, 2)

    def test_crlf_and_bom(self):
        path = os.path.join(self.mod, "common", "x.txt")
        os.makedirs(os.path.dirname(path))
        with open(path, "wb") as fh:
            fh.write('﻿a = {\r\n\ticon = "gfx/nope.dds"\r\n}\r\n'.encode("utf-8"))
        r = tra.audit(mod_path=self.mod, index=self.index)
        self.assertEqual([(f.line, f.value) for f in r.flags], [(2, "gfx/nope.dds")])


class SuppressionTests(_Fixture):
    def test_tag_suppresses_its_line(self):
        r = self.run_audit({"common/x.txt": (
            'a = "gfx/nope.dds" # REVIEWED 2026-10-26 (texture_reference): art lands in #9999\n'
            'b = "gfx/nope2.dds" # REVIEWED 2026-10-26 (script_argument): another check\n'
            'c = "gfx/nope3.dds" # REVIEWED 2026-10-26: untagged\n')})
        self.assertEqual([(f.line, bool(f.exemption)) for f in r.flags],
                         [(1, True), (2, False), (3, False)])
        self.assertEqual(r.flags[0].exemption,
                         {"date": "2026-10-26", "rationale": "art lands in #9999"})
        self.assertEqual(r.failing, 2)
        self.assertEqual(r.stale_tags, [])

    def test_tag_lines_count_newlines_only(self):
        # A stray form feed is a line break to str.splitlines(), not to the value scan.
        r = self.run_audit({"common/x.txt": (
            'a = 1 \x0c b = 2\n'
            'c = "gfx/nope.dds" # REVIEWED 2026-10-26 (texture_reference): art pending\n')})
        self.assertEqual([(f.line, bool(f.exemption)) for f in r.flags], [(2, True)])
        self.assertEqual(r.stale_tags, [])

    def test_multi_check_tag(self):
        r = self.run_audit({"common/x.txt":
                            'a = "gfx/nope.dds" # REVIEWED 2026-10-26 (script_argument, texture_reference): both\n'})
        self.assertTrue(r.flags[0].exemption)
        self.assertEqual(r.failing, 0)

    def test_stale_tag_fails(self):
        r = self.run_audit({"common/x.txt": (
            'a = "gfx/interface/icons/a.dds" # REVIEWED 2026-10-26 (texture_reference): was broken\n'
            '# REVIEWED 2026-10-26 (texture_reference): on a line with no path\n')})
        self.assertEqual(r.flags, [])
        self.assertEqual([(t.file, t.line) for t in r.stale_tags], [("common/x.txt", 1), ("common/x.txt", 2)])
        self.assertEqual(r.failing, 2)
        self.assertEqual(tra.summary(r)["unreviewed"], 2)
        self.assertEqual(tra.summary(r)["stale_tags"], 2)
        self.assertIn("## Stale tags", tra.render_report(r))

    def test_tag_on_dlc_only_is_not_stale(self):
        r = self.run_audit({"events/e.txt": (
            'e.1 = { event_image = { video = "dlc_alias" } } '
            '# REVIEWED 2026-10-26 (texture_reference): DLC-gated\n')})
        self.assertEqual([(f.kind, bool(f.exemption)) for f in r.flags], [("dlc_only", True)])
        self.assertEqual(r.stale_tags, [])

    def test_event_context_audit_ignores_the_tag(self):
        self.assertIn(tra.CHECK, event_context_audit.FOREIGN_CHECKS)


BG = 'background = "gfx/interface/icons/a.dds"'


class DeclarationTests(_Fixture):
    """#1182: an entity that names no art in a field its type needs."""

    def run_audit(self, files, index=None, gaps=None):
        _tree(self.mod, files)
        return tra.audit(mod_path=self.mod, index=index or self.index, vanilla_gaps=gaps or {})

    def undeclared(self, result):
        return [(f.file, f.line, f.value, f.key, bool(f.exemption))
                for f in result.flags if f.kind == "undeclared"]

    def test_building_without_background_flags(self):
        r = self.run_audit({"common/buildings/b.txt": (
            '﻿# a comment = { }\n'
            'building_ok = {\n'
            '\ticon = "gfx/interface/icons/a.dds"\n'
            f'\t{BG}\n'
            '}\n'
            'building_none = {\n'
            '\tbuilding_group = bg_x\n'
            '\ticon = "gfx/interface/icons/a.dds"\n'
            '}\n'
            'building_empty = { background = "" }\n')})
        self.assertEqual(self.undeclared(r), [
            ("common/buildings/b.txt", 6, "building_none", "background", False),
            ("common/buildings/b.txt", 10, "building_empty", "background", False)])
        self.assertEqual(r.failing, 2)
        self.assertEqual(r.entities_checked, 3)
        self.assertIn("`building_none` declares no `background`", tra.render_report(r))
        self.assertEqual(tra.summary(r)["undeclared"], 2)

    def test_inject_into_vanilla_is_not_the_mods(self):
        r = self.run_audit({"common/buildings/b.txt": 'INJECT:building_vanilla_farm = { level = 2 }\n'})
        self.assertEqual(self.undeclared(r), [])
        self.assertEqual(r.entities_checked, 0)

    def test_inject_into_a_mod_entity_counts_with_its_base(self):
        r = self.run_audit({
            "common/buildings/a.txt": 'building_x = { icon = x }\nbuilding_y = { icon = y }\n',
            "common/buildings/b.txt": f'INJECT:building_x = {{ {BG} }}\nINJECT:building_y = {{ level = 2 }}\n'})
        # building_x gets its background from the INJECT; building_y from nowhere,
        # flagged on its own opening line rather than the INJECT's.
        self.assertEqual(self.undeclared(r), [("common/buildings/a.txt", 2, "building_y", "background", False)])

    def test_replace_restates_the_whole_entity(self):
        files = {"common/production_method_groups/g.txt": (
            'REPLACE:pmg_aeroplanes = {\n'
            '\tproduction_methods = { pm_a }\n'
            '}\n'
            'REPLACE:pmg_dummy = { production_methods = { pm_dummy } }\n')}
        r = self.run_audit(files)
        self.assertEqual([v for _f, _l, v, _k, _e in self.undeclared(r)],
                         ["REPLACE:pmg_aeroplanes", "REPLACE:pmg_dummy"])
        # Vanilla's own pmg_dummy has no texture: the REPLACE may leave it out too.
        r = self.run_audit(files, gaps={"production_method_groups": {"texture": frozenset({"pmg_dummy"})}})
        self.assertEqual([v for _f, _l, v, _k, _e in self.undeclared(r)], ["REPLACE:pmg_aeroplanes"])
        self.assertEqual(r.vanilla_precedent, [("production_method_groups", "pmg_dummy", "texture")])
        self.assertIn("`pmg_dummy`: `texture`", tra.render_report(r))

    def test_no_building_group_fallback(self):
        # Neither vanilla nor the mod gives a building group art; the
        # name-carrier anchor logged the line in a group whose other buildings
        # all declare one.
        r = self.run_audit({
            "common/building_groups/g.txt": f'bg_x = {{ {BG} }}\n',
            "common/buildings/b.txt": (f'building_sibling = {{ building_group = bg_x {BG} }}\n'
                                       'building_x = { building_group = bg_x }\n')})
        self.assertEqual([v for _f, _l, v, _k, _e in self.undeclared(r)], ["building_x"])

    def test_nested_field_and_block_values(self):
        r = self.run_audit({
            "common/combat_unit_types/c.txt": (
                'unit_ok = {\n'
                '\tcombat_unit_image = { trigger = { always = yes } texture = "gfx/interface/icons/a.dds" }\n'
                '}\n'
                'unit_none = { combat_unit_image = { trigger = { always = yes } } }\n'
                'unit_wrong_level = { texture = "gfx/interface/icons/a.dds" }\n'),
            "common/parties/p.txt": 'party_ok = { icon = { default = "gfx/interface/icons/a.dds" } }\n'})
        self.assertEqual([(v, k) for _f, _l, v, k, _e in self.undeclared(r)],
                         [("unit_none", "combat_unit_image/texture"),
                          ("unit_wrong_level", "combat_unit_image/texture")])

    def test_only_registered_folders_and_real_entities(self):
        r = self.run_audit({
            "common/technology/eras/e.txt": 'era_9 = { technology_cost = 1 }\n',
            "common/technology/technologies/t.txt": (
                '@cost = 5\nscalar = 3\n'
                'tech_ok = { texture = "gfx/interface/icons/a.dds" era = era_1 }\n'
                'tech_none = { era = era_1 }\n'),
            "common/building_groups/g.txt": 'bg_y = { category = urban }\n'})
        self.assertEqual([v for _f, _l, v, _k, _e in self.undeclared(r)], ["tech_none"])
        self.assertEqual(r.entities_checked, 2)

    def test_tag_on_the_opening_line(self):
        r = self.run_audit({"common/buildings/b.txt": (
            'building_never_built = { # REVIEWED 2026-10-26 (texture_reference): never shown\n'
            '\tbuilding_group = bg_x\n'
            '}\n'
            'building_tag_inside = {\n'
            '\tbuilding_group = bg_x # REVIEWED 2026-10-26 (texture_reference): wrong line\n'
            '}\n'
            'building_untagged = { # REVIEWED 2026-10-26: another audit\'s\n'
            '}\n')})
        self.assertEqual([(v, e) for _f, _l, v, _k, e in self.undeclared(r)],
                         [("building_never_built", True), ("building_tag_inside", False),
                          ("building_untagged", False)])
        self.assertEqual(r.flags[0].exemption["rationale"], "never shown")
        # The tag inside the body suppresses nothing.
        self.assertEqual([(t.file, t.line) for t in r.stale_tags], [("common/buildings/b.txt", 5)])
        self.assertEqual(r.failing, 3)

    def test_stale_tag_on_an_entity_that_declares(self):
        r = self.run_audit({"common/buildings/b.txt": (
            f'building_fixed = {{ # REVIEWED 2026-10-26 (texture_reference): art pending\n\t{BG}\n}}\n')})
        self.assertEqual(r.flags, [])
        self.assertEqual([t.line for t in r.stale_tags], [1])
        self.assertEqual(r.failing, 1)

    def test_one_tag_covers_a_path_and_a_declaration_on_its_line(self):
        r = self.run_audit({"common/buildings/b.txt": (
            'building_x = { icon = "gfx/nope.dds" } # REVIEWED 2026-10-26 (texture_reference): both pending\n')})
        self.assertEqual(sorted(f.kind for f in r.flags), ["missing", "undeclared"])
        self.assertTrue(all(f.exemption for f in r.flags))
        self.assertEqual((r.failing, r.stale_tags), (0, []))

    def test_load_vanilla_gaps(self):
        snap = os.path.join(self.mod, "vanilla_parsed")
        _tree(snap, {
            "manifest.json": json.dumps({"entity_types": {
                "Modifiers": {"dir": "game/common/static_modifiers", "file": "common/modifiers.json"},
                "Combat Unit Types": {"dir": "game/common/combat_unit_types",
                                      "file": "common/combat_unit_types.json"},
                "Laws": {"dir": "game/common/laws", "file": "common/laws.json"}}}),
            "common/modifiers.json": json.dumps({
                "with_icon": ["=", {"icon": ["=", "gfx/a.dds"]}],
                "base_values": ["=", {"country_x_add": ["=", "1"]}],
                "empty_icon": ["=", {"icon": ["=", "\"\""]}]}),
            "common/combat_unit_types.json": json.dumps({
                "repeated": ["=", {"combat_unit_image": [
                    ["=", {"trigger": ["=", {}]}],
                    ["=", {"texture": ["=", "\"gfx/b.dds\""]}]]}],
                "none": ["=", {"combat_unit_image": ["=", {"trigger": ["=", {}]}]}]}),
            "common/laws.json": "not json"})
        gaps = tra.load_vanilla_gaps(self.mod)
        self.assertEqual(gaps, {"static_modifiers": {"icon": frozenset({"base_values", "empty_icon"})},
                                "combat_unit_types": {"combat_unit_image/texture": frozenset({"none"})}})
        self.assertEqual(tra.load_vanilla_gaps(os.path.join(self._tmp, "nowhere")), {})

    def test_committed_snapshot_bears_the_registry_out(self):
        # Each field is on every vanilla entity of its type but for these
        # (DECLARED_FIELDS' premise). A vanilla bump that rebuilds
        # vanilla_parsed/ and adds an exception fails here: re-check the field.
        root = os.path.dirname(os.path.abspath(__file__))
        gaps = tra.load_vanilla_gaps(root)
        expected = {("static_modifiers", "icon"): 32, ("production_methods", "texture"): 1,
                    ("production_method_groups", "texture"): 1}
        got = {(folder, f): len(names) for folder, d in gaps.items() for f, names in d.items() if names}
        self.assertEqual(got, expected,
                         "a vanilla entity of a DECLARED_FIELDS type no longer declares its field: "
                         "read it (an engine default? a dummy?), then drop the field or update the count")
        self.assertIn("pmg_dummy", gaps["production_method_groups"]["texture"])
        self.assertIn("buildings", gaps)  # the snapshot holds the logged type
        self.assertGreaterEqual(len(gaps), 20)

    def test_fields_with_an_engine_default_stay_out(self):
        # Optional by vanilla's own readmes: a JE falls back to
        # JOURNAL_ENTRY_ICON_DEFAULT, a harvest condition's map pattern is
        # "default - none", a terrain's `textures` are extras.
        self.assertNotIn("journal_entries", tra.DECLARED_FIELDS)
        self.assertNotIn("terrain", tra.DECLARED_FIELDS)
        self.assertEqual(tra.DECLARED_FIELDS["harvest_condition_types"][0], ("icon",))
        self.assertEqual(tra.DECLARED_FIELDS["buildings"][0], ("background",))  # not `icon`
        for folder, (fields, why) in tra.DECLARED_FIELDS.items():
            self.assertTrue(fields and why, folder)


class CatalogTests(_Fixture):
    def test_bootstrap_round_trip_and_agreement(self):
        info = tra.bootstrap_catalog(self.install, self.mod)
        self.assertEqual(info["version"], "9.9.9")
        self.assertEqual(tra.load_catalog(self.mod), tra.scan_install(self.install))
        with open(os.path.join(self.mod, tra.CATALOG_REL), encoding="utf-8") as fh:
            lines = [ln.rstrip("\n") for ln in fh if not ln.startswith("#")]
        self.assertIn("gfx/interface/icons/a.dds\tbase,dlc001_pack", lines)
        self.assertIn("gfx/event_pictures/dlc_video.bk2\tdlc001_pack", lines)
        self.assertIn("media_alias:base_alias", lines)
        self.assertNotIn("gfx/models/ship.mesh", lines)  # not an ASSET_EXTENSIONS file
        self.assertEqual(lines, sorted(ln for ln in lines if not ln.startswith("media_alias:"))
                         + sorted(ln for ln in lines if ln.startswith("media_alias:")))

        files = {"common/x.txt": (
            'a = "gfx/interface/icons/a.dds"\n'
            'b = "gfx/nope.dds"\n'
            'c = "gfx/interface/icons/mixed_case.dds"\n'
            'd = "gfx/event_pictures/dlc_video.bk2"\n'
            'e = { video = no_such_alias }\n')}
        _tree(self.mod, files)
        live, stale = tra.build_index(self.mod, source="install", base=self.install, mod_files=MOD_FILES)
        self.assertFalse(stale)
        offline, stale = tra.build_index(self.mod, source="catalog", mod_files=MOD_FILES)
        self.assertIsNone(stale)
        a = tra.audit(mod_path=self.mod, index=live)
        b = tra.audit(mod_path=self.mod, index=offline)
        self.assertEqual([tra.flag_dict(f) for f in a.flags], [tra.flag_dict(f) for f in b.flags])
        self.assertEqual(len(a.flags), 4)
        self.assertEqual(tra.render_report(a), tra.render_report(b))

    def test_stale_catalog_is_noticed(self):
        tra.bootstrap_catalog(self.install, self.mod)
        _tree(self.install, {"game/gfx/interface/icons/new_in_patch.dds": ""})
        _, stale = tra.build_index(self.mod, source="install", base=self.install, mod_files=MOD_FILES)
        self.assertTrue(stale)

    def test_no_catalog_and_no_install_raises(self):
        with self.assertRaises(FileNotFoundError):
            tra.build_index(self.mod, source="catalog", mod_files=MOD_FILES)

    def test_install_listing_is_cached_per_install_state(self):
        calls = []
        real = tra.scan_install

        def counting(base):
            calls.append(base)
            return real(base)

        self.addCleanup(tra._INSTALL_CACHE.clear)
        tra._INSTALL_CACHE.clear()
        with mock.patch.object(tra, "scan_install", side_effect=counting):
            tra.build_index(self.mod, source="install", base=self.install, mod_files=MOD_FILES)
            tra.build_index(self.mod, source="install", base=self.install, mod_files=MOD_FILES)
            self.assertEqual(len(calls), 1)
            _tree(self.install, {"launcher/launcher-settings.json": json.dumps({"rawVersion": "9.9.10"})})
            tra.build_index(self.mod, source="install", base=self.install, mod_files=MOD_FILES)
            self.assertEqual(len(calls), 2)
            _tree(self.install, {"game/dlc/dlc002_new/gfx/x.dds": ""})
            tra.build_index(self.mod, source="install", base=self.install, mod_files=MOD_FILES)
            self.assertEqual(len(calls), 3)

    def test_committed_catalog_matches_the_vanilla_snapshot(self):
        # A vanilla bump that rebuilds vanilla_parsed/ but skips --bootstrap
        # leaves CI resolving against the old file list; fail it here.
        root = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(root, "vanilla_parsed", "manifest.json"), encoding="utf-8") as fh:
            snapshot = json.load(fh)["game_version"]
        self.assertEqual(tra.catalog_version(root), snapshot,
                         "re-run `python3 texture_reference_audit.py --bootstrap` on the game install")

    def test_committed_catalog_parses(self):
        root = os.path.dirname(os.path.abspath(__file__))
        paths, aliases = tra.load_catalog(root)
        self.assertGreater(len(paths), 10000)
        self.assertIn("gfx/FX/pdxgui_default.shader", paths)  # clausewitz's mount
        self.assertIn("unspecific_world_fair", aliases)
        self.assertTrue(all(p.startswith("gfx/") and p.lower().endswith(tra.ASSET_EXTENSIONS) for p in paths))


class GitTests(unittest.TestCase):
    def test_tracked_files_come_from_the_index_not_the_disk(self):
        with tempfile.TemporaryDirectory() as mod:
            _tree(mod, {"gfx/tracked.dds": "", "gfx/sub/also.dds": "", "gfx/untracked.dds": ""})
            subprocess.run(["git", "init", "-q", mod], check=True)
            subprocess.run(["git", "-C", mod, "add", "gfx/tracked.dds", "gfx/sub/also.dds"], check=True)
            os.remove(os.path.join(mod, "gfx", "tracked.dds"))  # a sparse checkout
            self.assertEqual(tra.mod_gfx_files(mod), {"gfx/tracked.dds", "gfx/sub/also.dds"})

    def test_mod_aliases_read_from_the_index_when_off_disk(self):
        with tempfile.TemporaryDirectory() as mod:
            _tree(mod, {"gfx/media_aliases/te.txt": "te_alias = { video = \"x\" }\n"})
            subprocess.run(["git", "init", "-q", mod], check=True)
            subprocess.run(["git", "-C", mod, "add", "gfx/media_aliases/te.txt"], check=True)
            os.remove(os.path.join(mod, "gfx", "media_aliases", "te.txt"))
            files = tra.mod_gfx_files(mod)
            self.assertEqual(tra.mod_media_aliases(mod, files), {"te_alias"})

    def test_outside_git_falls_back_to_the_disk(self):
        with tempfile.TemporaryDirectory() as mod:
            _tree(mod, {"gfx/a.dds": ""})
            with mock.patch.object(tra.subprocess, "run", side_effect=subprocess.CalledProcessError(128, "git")):
                self.assertEqual(tra.mod_gfx_files(mod), {"gfx/a.dds"})


class EntryPointTests(_Fixture):
    def _patched(self):
        return mock.patch.multiple(path_constants, create=True, mod_path=self.mod,
                                   base_game_path=self.install)

    def test_regenerate_writes_the_report(self):
        _tree(self.mod, {"common/x.txt": 'a = "gfx/nope.dds"\n'})
        with self._patched(), mock.patch.object(tra, "mod_gfx_files", return_value=set(MOD_FILES)):
            out = tra.regenerate(None)
        self.assertEqual(out["unreviewed"], 1)
        self.assertEqual(out["vanilla_source"], "install")
        self.assertTrue(out["catalog_stale"])  # no catalog in the fixture
        with open(out["path"], encoding="utf-8") as fh:
            self.assertIn("gfx/nope.dds", fh.read())

    def test_main_strict_exit_codes(self):
        tra.bootstrap_catalog(self.install, self.mod)
        with self._patched(), mock.patch.object(tra, "mod_gfx_files", return_value=set(MOD_FILES)), \
                mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            _tree(self.mod, {"common/x.txt": 'a = "gfx/interface/icons/a.dds"\n'})
            self.assertEqual(tra.main(["--strict", "--source", "catalog"]), 0)
            _tree(self.mod, {"common/x.txt": 'a = "gfx/nope.dds"\n'})
            self.assertEqual(tra.main(["--strict", "--source", "catalog"]), 1)
            self.assertEqual(tra.main(["--source", "catalog"]), 0)


if __name__ == "__main__":
    unittest.main()
