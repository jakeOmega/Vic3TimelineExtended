"""Unit tests for /placeholder-icons (`_find_placeholder_icons` and helpers in
mod_state_server).

They run on a fake ModState, a fake `origin` (which file a path resolves to)
and a fake `hasher`, so no .dds file or game install is needed.

Run: python3 test_placeholder_icons.py
"""
import os
import tempfile
import unittest
from unittest import mock

import mod_state_server as srv
from test_duplicate_images import _entity, _install_fake_ms


MOD_FILES = {
    "gfx/law/a.dds": "md5:a",
    "gfx/law/b.dds": "md5:b",
    "gfx/law/b_copy.dds": "md5:b",
    "gfx/company/acme.dds": "md5:acme",
    "gfx/pm/cat_gear_gold_p0.dds": "md5:gear",
}
VANILLA_FILES = {"gfx/law/vanilla.dds", "gfx/modifier/vanilla.dds", "gfx/p/x.dds"}


def _origin(path):
    if path in MOD_FILES:
        return "mod", f"/mod/{path}"
    if path in VANILLA_FILES:
        return "vanilla", f"/game/{path}"
    return None


def _hasher(path):
    return MOD_FILES.get(path, f"path:{path}")


def _run(**kwargs):
    kwargs.setdefault("standin_patterns", ["gfx/pm/cat_*.dds"])
    kwargs.setdefault("allowlist", {})
    kwargs.setdefault("origin", _origin)
    kwargs.setdefault("hasher", _hasher)
    kwargs.setdefault("vanilla_gfx", True)
    return srv._find_placeholder_icons(**kwargs)


def _by_key(report):
    return {(e["entity_type"], e["key"], e["field"]): e for e in report["entities"]}


class _FakeMSCase(unittest.TestCase):
    def setUp(self):
        self.original_ms = None

    def tearDown(self):
        if self.original_ms is not None:
            srv.ms = self.original_ms

    def install(self, mod, base=None):
        self.original_ms = _install_fake_ms(mod, base=base)


class StatusTests(_FakeMSCase):
    def test_each_status(self):
        self.install({"Laws": {
            "law_missing": _entity(icon="gfx/law/nowhere.dds"),
            "law_borrowed": _entity(icon="gfx/law/vanilla.dds"),
            "law_unique": _entity(icon="gfx/law/a.dds"),
            "law_shared_1": _entity(icon="gfx/law/b.dds"),
            "law_shared_2": _entity(icon="gfx/law/b_copy.dds"),
        }})
        entries = _by_key(_run())
        status = {k[1]: e["status"] for k, e in entries.items()}
        self.assertEqual(status, {
            "law_missing": "missing",
            "law_borrowed": "borrowed_vanilla",
            "law_unique": "unique_mod",
            "law_shared_1": "shared_mod",
            "law_shared_2": "shared_mod",
        })
        # Byte-identical files under two names are one picture.
        self.assertEqual(entries[("Laws", "law_shared_1", "icon")]["shared_with"],
                         ["law_shared_2"])

    def test_untouched_vanilla_entity_is_not_reported(self):
        vanilla = {"law_v": _entity(icon="gfx/law/vanilla.dds")}
        self.install({"Laws": {**vanilla, "law_m": _entity(icon="gfx/law/vanilla.dds")}},
                     base={"Laws": vanilla})
        entries = _by_key(_run())
        self.assertEqual(list(entries), [("Laws", "law_m", "icon")])
        # The vanilla user still shows as a sharer.
        self.assertEqual(entries[("Laws", "law_m", "icon")]["shared_with"], ["law_v"])

    def test_vanilla_entity_the_mod_re_icons_is_reported(self):
        self.install({"Laws": {"law_v": _entity(icon="gfx/law/a.dds")}},
                     base={"Laws": {"law_v": _entity(icon="gfx/law/vanilla.dds")}})
        self.assertEqual(_by_key(_run())[("Laws", "law_v", "icon")]["status"], "unique_mod")

    def test_sharing_across_types(self):
        # A treaty article on a mod law's icon: both are shared, and the other
        # type is named.
        self.install({
            "Laws": {"law_peg": _entity(icon="gfx/law/a.dds")},
            "Treaty Articles": {"currency_peg": _entity(icon="gfx/law/a.dds")},
        })
        entries = _by_key(_run())
        self.assertEqual(entries[("Treaty Articles", "currency_peg", "icon")]["shared_with"],
                         ["Laws:law_peg"])
        self.assertEqual(entries[("Laws", "law_peg", "icon")]["status"], "shared_mod")

    def test_shared_with_is_capped_same_type_first(self):
        laws = {f"law_{i:02d}": _entity(icon="gfx/law/vanilla.dds") for i in range(25)}
        self.install({"Laws": laws,
                      "Decrees": {"decree_a": _entity(texture="gfx/law/vanilla.dds")}},
                     base={"Laws": {k: v for k, v in laws.items() if k != "law_00"}})
        entry = _by_key(_run())[("Laws", "law_00", "icon")]
        self.assertEqual(entry["shared_count"], 25)
        self.assertEqual(len(entry["shared_with"]), srv._SHARED_WITH_LIMIT)
        self.assertEqual(entry["shared_with"][0], "law_01")
        self.assertNotIn("Decrees:decree_a", entry["shared_with"])
        text = srv._render_placeholder_icons_text(_run())
        self.assertIn("and 5 more", text)

    def test_allowlisted_share_carries_its_reason(self):
        self.install({"Laws": {
            "law_reviewed": _entity(icon="gfx/law/vanilla.dds"),
            "law_open": _entity(icon="gfx/law/a.dds"),
        }})
        allowlist = {"Laws": {
            (frozenset({"gfx/law/vanilla.dds"}),
             frozenset({"law_reviewed", "law_vanilla"})): "a deliberate pick",
        }}
        report = _run(allowlist=allowlist)
        entries = _by_key(report)
        self.assertEqual(entries[("Laws", "law_reviewed", "icon")]["allowlisted"],
                         "a deliberate pick")
        self.assertNotIn("allowlisted", entries[("Laws", "law_open", "icon")])
        self.assertIn("allowlisted: a deliberate pick",
                      srv._render_placeholder_icons_text(report))

    def test_generated_standin_takes_precedence(self):
        self.install({"Laws": {
            "law_a": _entity(icon="gfx/pm/cat_gear_gold_p0.dds"),
            "law_b": _entity(icon="gfx/pm/cat_gear_gold_p0.dds"),
        }})
        statuses = {e["status"] for e in _run()["entities"]}
        self.assertEqual(statuses, {"generated_standin"})

    def test_without_vanilla_gfx_outside_paths_are_unresolved(self):
        self.install({"Laws": {
            "law_borrowed": _entity(icon="gfx/law/vanilla.dds"),
            "law_unique": _entity(icon="gfx/law/a.dds"),
        }})
        report = _run(vanilla_gfx=False, origin=lambda p: _origin(p) if p in MOD_FILES else None)
        status = {e["key"]: e["status"] for e in report["entities"]}
        self.assertEqual(status, {"law_borrowed": "unresolved", "law_unique": "unique_mod"})
        self.assertTrue(report["warnings"])


class SharedByDesignTests(_FakeMSCase):
    def setUp(self):
        super().setUp()
        self.install({
            "Laws": {"law_a": _entity(icon="gfx/law/a.dds")},
            "Modifiers": {
                "mod_borrowed": _entity(icon="gfx/modifier/vanilla.dds"),
                "mod_broken": _entity(icon="gfx/modifier/typo.dds"),
                "mod_on_law_icon": _entity(icon="gfx/law/a.dds"),
            },
        })

    def test_only_missing_by_default(self):
        entries = _by_key(_run())
        self.assertEqual(entries[("Modifiers", "mod_broken", "icon")]["status"], "missing")
        self.assertNotIn(("Modifiers", "mod_borrowed", "icon"), entries)
        # A by-design user doesn't make a strict icon shared.
        self.assertEqual(entries[("Laws", "law_a", "icon")]["status"], "unique_mod")

    def test_flag_classifies_them(self):
        entries = _by_key(_run(include_shared_by_design=True))
        self.assertEqual(entries[("Modifiers", "mod_borrowed", "icon")]["status"],
                         "borrowed_vanilla")
        self.assertEqual(entries[("Laws", "law_a", "icon")]["status"], "shared_mod")


class FlagshipTests(_FakeMSCase):
    def test_flagship_on_its_company_logo_is_left_out(self):
        self.install({
            "Company Types": {"company_acme": _entity(
                icon="gfx/company/acme.dds", building_types=["building_acme_works"])},
            "Buildings": {"building_acme_works": _entity(
                icon="gfx/company/acme.dds", building_group="bg_company_buildings")},
        })
        entries = _by_key(_run())
        self.assertNotIn(("Buildings", "building_acme_works", "icon"), entries)
        self.assertEqual(entries[("Company Types", "company_acme", "icon")]["status"],
                         "unique_mod")

    def test_flagship_on_another_icon_is_classified(self):
        self.install({
            "Company Types": {"company_acme": _entity(
                icon="gfx/company/acme.dds", building_types=["building_acme_works"])},
            "Buildings": {"building_acme_works": _entity(
                icon="gfx/law/vanilla.dds", building_group="bg_company_buildings")},
        })
        entries = _by_key(_run())
        self.assertEqual(entries[("Buildings", "building_acme_works", "icon")]["status"],
                         "borrowed_vanilla")


class PrincipleTests(_FakeMSCase):
    def test_mod_tier_on_its_vanilla_groups_icon_is_not_reported(self):
        vanilla_tiers = {"principle_x_1": _entity(icon="gfx/p/x.dds")}
        vanilla_groups = {"principle_group_x": _entity(levels=["principle_x_1"])}
        self.install({
            "Principles": {**vanilla_tiers,
                           "principle_x_4": _entity(icon="gfx/p/x.dds"),
                           "principle_new_1": _entity(icon="gfx/p/x.dds"),
                           "principle_new_2": _entity(icon="gfx/p/x.dds")},
            "Principle Groups": {
                "principle_group_x": _entity(levels=["principle_x_1", "principle_x_4"]),
                "principle_group_new": _entity(levels=["principle_new_1", "principle_new_2"]),
            },
        }, base={"Principles": vanilla_tiers, "Principle Groups": vanilla_groups})
        entries = _by_key(_run())
        self.assertEqual(list(entries), [("Principles", "principle_group_new", "icon")])
        entry = entries[("Principles", "principle_group_new", "icon")]
        self.assertEqual(entry["status"], "borrowed_vanilla")
        self.assertEqual(entry["members"], ["principle_new_1", "principle_new_2"])
        self.assertEqual(entry["shared_with"], ["principle_group_x"])


class FilterAndTextTests(_FakeMSCase):
    def setUp(self):
        super().setUp()
        self.install({
            "Laws": {"law_borrowed": _entity(icon="gfx/law/vanilla.dds"),
                     "law_unique": _entity(icon="gfx/law/a.dds")},
            "Decrees": {"decree_borrowed": _entity(texture="gfx/law/vanilla.dds")},
        })

    def test_status_filter_keeps_full_summary(self):
        report = _run(statuses=["borrowed_vanilla"])
        self.assertEqual({e["key"] for e in report["entities"]},
                         {"law_borrowed", "decree_borrowed"})
        self.assertEqual(report["summary"]["Laws"]["unique_mod"], 1)

    def test_type_filter(self):
        report = _run(types=["Decrees"])
        self.assertEqual(list(report["summary"]), ["Decrees"])
        self.assertEqual([e["key"] for e in report["entities"]], ["decree_borrowed"])
        # Sharing still sees the other types.
        self.assertEqual(report["entities"][0]["shared_with"], ["Laws:law_borrowed"])

    def test_text_collapses_unique_unless_asked(self):
        report = _run()
        text = srv._render_placeholder_icons_text(report)
        self.assertIn("BORROWED_VANILLA (2):", text)
        self.assertIn("UNIQUE_MOD (1): not listed", text)
        self.assertNotIn("law_unique", text)
        text = srv._render_placeholder_icons_text(report, list_unique=True)
        self.assertIn("law_unique", text)

    def test_handler_rejects_unknown_status(self):
        handler = srv.ModStateHandler.__new__(srv.ModStateHandler)
        with self.assertRaises(srv.BadRequest):
            handler._placeholder_icons({"status": ["borrowed"]})


class DefinitionSiteTests(unittest.TestCase):
    def test_field_line_opener_fallback_and_inject_order(self):
        with tempfile.TemporaryDirectory() as root:
            laws = os.path.join(root, "common", "laws")
            os.makedirs(laws)
            with open(os.path.join(laws, "a_laws.txt"), "w", encoding="utf-8-sig") as f:
                f.write("law_x = {\n"
                        "\tgroup = lawgroup_x\n"
                        "\ticon = \"gfx/law/a.dds\"\n"
                        "\tmodifier = { icon = \"not/this.dds\" }\n"
                        "}\n"
                        "law_no_icon = {  # comment with { brace\n"
                        "\tgroup = lawgroup_x\n"
                        "}\n")
            with open(os.path.join(laws, "b_inject.txt"), "w", encoding="utf-8-sig") as f:
                f.write("INJECT:law_x = {\n"
                        "\ticon = \"gfx/law/b.dds\"\n"
                        "}\n")
            with mock.patch.object(srv, "mod_path", root), \
                    mock.patch.dict(srv.mod_paths, {"Laws": laws}):
                sites = srv._icon_definition_sites("Laws", "icon")
        self.assertEqual(sites["law_x"], (os.path.join("common", "laws", "b_inject.txt"), 2))
        self.assertEqual(sites["law_no_icon"], (os.path.join("common", "laws", "a_laws.txt"), 6))


class StandinPatternTests(unittest.TestCase):
    def test_committed_patterns_load(self):
        patterns = srv._load_standin_patterns()
        self.assertIn("gfx/interface/icons/production_method_icons/cat_*.dds", patterns)

    def test_missing_file_returns_empty(self):
        self.assertEqual(srv._load_standin_patterns("/nonexistent/standins.yml"), [])


if __name__ == "__main__":
    unittest.main()
