"""gui_placeholder_textures: vanilla textures in the mod's own GUI widgets (#1484), without a game."""
import os
import tempfile
import unittest
from unittest import mock

import gui_placeholder_textures as gpt
import mod_state_server as mss

ROOT = os.path.dirname(os.path.abspath(__file__))

WIDGET = '''types te_widgets {
	type te_row = hbox {
		icon = {
			texture = "gfx/interface/icons/lens_toolbar_icons/trade_agreement.dds"	# a stand-in
		}
		icon = { texture = "gfx/interface/icons/te_icons/own_art.dds" }
		icon = { texture = "gfx/interface/icons/generic_icons/trend_up.dds" }
		background = { texture = "gfx/interface/backgrounds/white.dds" }
		icon = { texture = "[Goods.GetTexture]" }
		# icon = { texture = "gfx/interface/icons/commented/out.dds" }
		progressbar = {
			progresstexture = "gfx/interface/progressbar/progress_green.dds"
			noprogresstexture = "gfx/interface/icons/nowhere/gone.dds"
		}
		icon = { texture = "gfx/interface/icons/lens_toolbar_icons/trade_agreement.dds" }
		icon = { texture = "gfx/interface/icons/generic_icons/warning.dds" }
		icon = { texture = "gfx/interface/icons/goods_icons/grain.dds" }
	}
}
'''
OVERRIDE = 'window = { icon = { texture = "gfx/interface/icons/goods_icons/grain.dds" } }\n'
DOC = '''# Widget icons

| Cell | Shows | File |
|---|---|---|
| risk | vanilla's warning mark, kept | `gfx/interface/icons/generic_icons/warning.dds` |
| trade | a placeholder until the handshake is drawn | `gfx/interface/icons/lens_toolbar_icons/trade_agreement.dds` |
| own | the mod's art | `gfx/interface/icons/te_icons/own_art.dds` |
'''
VANILLA = {"gfx/interface/icons/lens_toolbar_icons/trade_agreement.dds",
           "gfx/interface/icons/generic_icons/trend_up.dds", "gfx/interface/backgrounds/white.dds",
           "gfx/interface/progressbar/progress_green.dds", "gfx/interface/icons/generic_icons/warning.dds",
           "gfx/interface/icons/goods_icons/grain.dds"}
MOD = {"gfx/interface/icons/te_icons/own_art.dds"}


def resolve(path):
    return "mod" if path in MOD else "vanilla" if path in VANILLA else "missing"


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(text)


class _Tree(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.mod = tmp.name
        _write(self.mod, "gui/te_widgets.gui", WIDGET)
        _write(self.mod, "gui/panels/budget_panel.gui", OVERRIDE)
        _write(self.mod, "gui/notes.txt", 'texture = "gfx/interface/icons/x.dds"\n')
        _write(self.mod, "docs/systems/widget_gui_icons.md", DOC)
        self.vanilla_gui = {"gui/panels/budget_panel.gui", "gui/other.gui"}

    def run_report(self, **kwargs):
        return gpt.report(self.mod, self.vanilla_gui, resolve, **kwargs)


class ScanTests(unittest.TestCase):
    def test_literal_paths_outside_comments_with_their_property(self):
        refs = gpt.texture_refs(WIDGET)
        self.assertEqual(refs[0], (4, "texture", "gfx/interface/icons/lens_toolbar_icons/trade_agreement.dds"))
        paths = [p for _line, _key, p in refs]
        self.assertNotIn("gfx/interface/icons/commented/out.dds", paths)
        self.assertEqual(len(paths), 9)
        self.assertIn((12, "progresstexture", "gfx/interface/progressbar/progress_green.dds"), refs)
        self.assertIn((13, "noprogresstexture", "gfx/interface/icons/nowhere/gone.dds"), refs)

    def test_a_hash_inside_a_string_is_not_a_comment(self):
        refs = gpt.texture_refs('text = "#bold x#!" texture = "gfx/a.dds"\n')
        self.assertEqual(refs, [(1, "texture", "gfx/a.dds")])

    def test_kinds(self):
        self.assertEqual(gpt.kind_of("gfx/interface/icons/generic_icons/trend_up.dds"), "ui_mark")
        self.assertEqual(gpt.kind_of("gfx/interface/icons/generic_icons/transparent.dds"), "ui_mark")
        self.assertEqual(gpt.kind_of("gfx/interface/icons/generic_icons/warning.dds"), "ui_mark")
        self.assertEqual(gpt.kind_of("gfx/interface/icons/generic_icons/population.dds"), "icon")
        self.assertEqual(gpt.kind_of("gfx/interface/icons/goods_icons/grain.dds"), "icon")
        self.assertEqual(gpt.kind_of("gfx/interface/backgrounds/white.dds"), "chrome")


class ReportTests(_Tree):
    def rows(self, body, file="gui/te_widgets.gui"):
        entry = next(f for f in body["files"] if f["file"] == file)
        return {r["path"].rsplit("/", 1)[-1]: r for r in entry["textures"]}

    def test_only_the_mods_own_widgets_by_default(self):
        body = self.run_report()
        self.assertEqual([f["file"] for f in body["files"]], ["gui/te_widgets.gui"])
        self.assertTrue(body["files"][0]["mod_owned"])
        self.assertEqual((body["summary"]["mod_owned_files"], body["summary"]["override_files"]), (1, 1))

    def test_each_texture_once_with_its_uses_and_lines(self):
        rows = self.rows(self.run_report())
        trade = rows["trade_agreement.dds"]
        self.assertEqual((trade["uses"], trade["lines"], trade["keys"]), (2, [4, 15], ["texture"]))
        self.assertNotIn("own_art.dds", rows, "the mod's own art is not a stand-in")
        self.assertEqual(rows["gone.dds"]["resolves"], "missing")

    def test_the_work_list_is_vanilla_icons_no_doc_names(self):
        body = self.run_report()
        rows = self.rows(body)
        self.assertEqual([name for name, r in rows.items() if r["unlisted"]], ["grain.dds"])
        self.assertEqual(rows["trade_agreement.dds"]["listed_in"],
                         {"doc": "docs/systems/widget_gui_icons.md", "line": 6, "status": "placeholder"})
        self.assertEqual(rows["warning.dds"]["listed_in"]["status"], "kept")
        self.assertEqual((rows["trend_up.dds"]["kind"], rows["trend_up.dds"]["unlisted"]), ("ui_mark", False))
        self.assertEqual((rows["white.dds"]["kind"], rows["white.dds"]["unlisted"]), ("chrome", False))
        self.assertFalse(rows["gone.dds"]["unlisted"])
        self.assertEqual(body["summary"], {
            "mod_owned_files": 1, "override_files": 1, "vanilla_textures": 6, "vanilla_icons": 2,
            "missing": 1, "listed": 1, "unlisted": 1})
        self.assertEqual(list(rows)[0], "grain.dds", "the work list comes first")

    def test_overrides_on_request_are_never_on_the_work_list(self):
        body = self.run_report(include_overrides=True)
        rows = self.rows(body, "gui/panels/budget_panel.gui")
        self.assertFalse(next(f for f in body["files"] if f["file"] == "gui/panels/budget_panel.gui")["mod_owned"])
        self.assertFalse(rows["grain.dds"]["unlisted"])
        self.assertEqual(body["summary"]["unlisted"], 1)

    def test_unlisted_only_and_one_file(self):
        body = self.run_report(unlisted_only=True)
        self.assertEqual([r["path"] for r in body["files"][0]["textures"]],
                         ["gfx/interface/icons/goods_icons/grain.dds"])
        body = self.run_report(files=["gui/panels/budget_panel.gui"])
        self.assertEqual(body["files"], [])
        self.assertEqual(body["summary"]["mod_owned_files"], 0)

    def test_text_form_names_the_work_list(self):
        text = gpt.render_text(self.run_report())
        self.assertIn("1 mod-owned GUI files (1 overrides of vanilla panels left out)", text)
        self.assertIn("UNLISTED", text)
        self.assertIn("docs/systems/widget_gui_icons.md:6 (placeholder)", text)


class ListTests(_Tree):
    def test_bootstrap_lists_every_mount_and_reads_back(self):
        base = os.path.join(self.mod, "install")
        for rel in ("game/gui/a.gui", "game/gui/sub/b.gui", "jomini/gui/c.gui", "clausewitz/gui/d.gui",
                    "game/gfx/not_gui.dds"):
            _write(base, rel, "x")
        out = gpt.bootstrap(base, self.mod, "1.15.1")
        self.assertEqual(out["gui_files"], 4)
        self.assertEqual(gpt.load_gui_files(self.mod),
                         frozenset({"gui/a.gui", "gui/sub/b.gui", "gui/c.gui", "gui/d.gui"}))
        self.assertFalse(gpt.list_is_stale(base, self.mod))
        _write(base, "game/gui/new.gui", "x")
        self.assertTrue(gpt.list_is_stale(base, self.mod))
        self.assertIsNone(gpt.list_is_stale(None, self.mod))
        self.assertIsNone(gpt.list_is_stale(os.path.join(self.mod, "no install"), self.mod))

    def test_a_missing_list_raises(self):
        with self.assertRaises(FileNotFoundError):
            gpt.load_gui_files(self.mod)

    def test_the_committed_list_tells_the_mods_widgets_from_its_overrides(self):
        vanilla = gpt.load_gui_files(ROOT)
        self.assertGreater(len(vanilla), 300)
        self.assertTrue(all(f.startswith("gui/") for f in vanilla))
        mine = gpt.mod_gui_files(ROOT)
        owned = [f for f in mine if f not in vanilla]
        # Files of both kinds exist, and neither a te_ prefix nor its absence says which a file is.
        self.assertIn("gui/te_grid_widgets.gui", owned)
        self.assertIn("gui/journal_entry_widgets/banking_dashboard_widget.gui", owned)
        self.assertTrue(set(mine) - set(owned), "the mod overrides some vanilla panels")


class EndpointTests(_Tree):
    def setUp(self):
        super().setUp()
        os.makedirs(os.path.join(self.mod, "docs", "engine"), exist_ok=True)
        with open(os.path.join(self.mod, gpt.GUI_FILES_REL), "w", encoding="utf-8") as f:
            f.write("# header\ngui/panels/budget_panel.gui\n")
        index = mock.Mock()
        index.resolve_path = lambda path: (resolve(path), "")
        index.source = "catalog"
        for target, name, value in ((mss, "mod_path", self.mod), (mss, "_vanilla_tree_present", lambda: False)):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        import texture_reference_audit
        p = mock.patch.object(texture_reference_audit, "build_index", lambda mod_path: (index, None))
        p.start()
        self.addCleanup(p.stop)
        self.handler = object.__new__(mss.ModStateHandler)

    def request(self, path):
        self.handler.path = path
        self.handler._local_request_ok = mock.Mock(return_value=True)
        self.handler._respond_json = mock.Mock()
        self.handler.do_GET()
        args = self.handler._respond_json.call_args.args
        return (args[1] if len(args) > 1 else 200), args[0]

    def test_the_endpoint_serves_the_report(self):
        status, body = self.request("/gui/placeholder-textures")
        self.assertEqual(status, 200)
        self.assertEqual(body["summary"]["unlisted"], 1)
        self.assertEqual((body["vanilla_source"], body["gui_file_list_stale"]), ("catalog", None))
        self.assertEqual([f["file"] for f in body["files"]], ["gui/te_widgets.gui"])

    def test_flags_and_the_text_form(self):
        _status, body = self.request("/gui/placeholder-textures?include_overrides=true")
        self.assertEqual(len(body["files"]), 2)
        _status, body = self.request("/gui/placeholder-textures?unlisted_only=true&format=text")
        self.assertIn("UNLISTED", body["text"])
        self.assertEqual(body["summary"]["unlisted"], 1)

    def test_an_unknown_file_is_a_404_and_a_missing_list_a_503(self):
        status, body = self.request("/gui/placeholder-textures?file=gui/te_widgts.gui")
        self.assertEqual(status, 404)
        self.assertIn("gui/te_widgets.gui", body["did_you_mean"])
        os.remove(os.path.join(self.mod, gpt.GUI_FILES_REL))
        status, body = self.request("/gui/placeholder-textures")
        self.assertEqual(status, 503)
        self.assertIn("--bootstrap", body["hint"])


if __name__ == "__main__":
    unittest.main()
