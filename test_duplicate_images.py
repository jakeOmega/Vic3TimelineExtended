"""Unit tests for the /duplicate-images helpers in mod_state_server.

These exercise the pure helper `_find_duplicate_images` directly with a fake
ModState (mod_parsers + base_parsers), so they don't need a running server.

The vanilla-sanity test at the bottom is gated behind
VIC3_RUN_VANILLA_TESTS=1 because it loads the full vanilla install (~60–90s).

Run: python3 test_duplicate_images.py
"""
import os
import unittest

import mod_state_server as srv


# ---------------------------------------------------------------------------
# Fake ModState — exposes mod_parsers + base_parsers so we can simulate both
# vanilla and mod entities, plus the mod-only filtering path.
# ---------------------------------------------------------------------------
class _FakeParser:
    def __init__(self, data: dict):
        self.data = data


class _FakeMS:
    def __init__(self, mod: dict, base: dict | None = None, loc: dict | None = None):
        # mod / base shape: {entity_type: {entity_id: ('=', {fields})}}
        base = base or {}
        all_types = set(mod) | set(base)
        self.mod_parsers = {et: _FakeParser(mod.get(et, {})) for et in all_types}
        self.base_parsers = {et: _FakeParser(base.get(et, {})) for et in all_types}
        self._loc = loc or {}

    def get_data(self, entity_type):
        parser = self.mod_parsers.get(entity_type)
        return parser.data if parser else None

    def localize(self, key):
        return self._loc.get(key, key)


def _eq(value):
    return ("=", value)


def _entity(**fields):
    """Build an entity tuple ('=', {field: ('=', value), ...})."""
    return _eq({k: _eq(v) for k, v in fields.items()})


def _install_fake_ms(mod, base=None):
    """Swap srv.ms for a fake. Returns the original to restore in tearDown."""
    fake = _FakeMS(mod, base=base)
    original = srv.ms
    srv.ms = fake
    return original


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------
class DuplicateDetectionTests(unittest.TestCase):
    def setUp(self):
        self.original_ms = None

    def tearDown(self):
        if self.original_ms is not None:
            srv.ms = self.original_ms

    def test_detects_basic_duplicate(self):
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/icons/shared.dds"),
            "building_b": _entity(icon="gfx/icons/shared.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        report = srv._find_duplicate_images(allowlist={})
        self.assertEqual(report["summary"]["flagged"], 1)
        flagged = report["flagged"][0]
        self.assertEqual(flagged["entity_type"], "Buildings")
        self.assertEqual(flagged["images"], ["gfx/icons/shared.dds"])
        self.assertEqual(sorted(flagged["entities"]), ["building_a", "building_b"])
        self.assertEqual(flagged["kind"], "path")

    def test_unique_images_produce_no_findings(self):
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/icons/a.dds"),
            "building_b": _entity(icon="gfx/icons/b.dds"),
            "building_c": _entity(icon="gfx/icons/c.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        report = srv._find_duplicate_images(allowlist={})
        self.assertEqual(report["summary"]["flagged"], 0)
        self.assertEqual(report["flagged"], [])

    def test_skips_permissive_types(self):
        # Events sharing a picture should NOT show up — they're a permissive type.
        # If srv processes Events, this would flag.
        mod = {
            "Events": {
                "event_a": _entity(picture="event_pic.dds"),
                "event_b": _entity(picture="event_pic.dds"),
            },
            "Buildings": {
                "building_a": _entity(icon="gfx/icons/unique.dds"),
            },
        }
        self.original_ms = _install_fake_ms(mod)
        report = srv._find_duplicate_images(allowlist={})
        self.assertEqual(report["summary"]["flagged"], 0)
        # Events must not appear in the scanned types list either.
        self.assertNotIn("Events", report["summary"]["scanned_entity_types"])

    def test_multiple_entity_types_in_one_report(self):
        mod = {
            "Buildings": {
                "building_a": _entity(icon="b_shared.dds"),
                "building_b": _entity(icon="b_shared.dds"),
            },
            "Goods": {
                "good_a": _entity(texture="g_shared.dds"),
                "good_b": _entity(texture="g_shared.dds"),
            },
        }
        self.original_ms = _install_fake_ms(mod)
        report = srv._find_duplicate_images(allowlist={})
        self.assertEqual(report["summary"]["flagged"], 2)
        types_flagged = sorted(f["entity_type"] for f in report["flagged"])
        self.assertEqual(types_flagged, ["Buildings", "Goods"])

    def test_type_filter(self):
        mod = {
            "Buildings": {
                "building_a": _entity(icon="b_shared.dds"),
                "building_b": _entity(icon="b_shared.dds"),
            },
            "Goods": {
                "good_a": _entity(texture="g_shared.dds"),
                "good_b": _entity(texture="g_shared.dds"),
            },
        }
        self.original_ms = _install_fake_ms(mod)
        report = srv._find_duplicate_images(allowlist={}, types=["Buildings"])
        self.assertEqual(report["summary"]["flagged"], 1)
        self.assertEqual(report["flagged"][0]["entity_type"], "Buildings")
        self.assertEqual(report["summary"]["scanned_entity_types"], ["Buildings"])


# ---------------------------------------------------------------------------
# Content-hash detection: different paths, identical bytes.
# Tests inject a fake hasher so they don't depend on real .dds files.
# ---------------------------------------------------------------------------
class ContentHashTests(unittest.TestCase):
    def setUp(self):
        self.original_ms = None

    def tearDown(self):
        if self.original_ms is not None:
            srv.ms = self.original_ms

    def test_distinct_paths_identical_content_are_flagged(self):
        # Three buildings with three different paths but the hasher reports
        # all three resolve to the same content hash → one cluster.
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/a.dds"),
            "building_b": _entity(icon="gfx/b.dds"),
            "building_c": _entity(icon="gfx/c.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        # Fake hasher: a/b/c → same hash; everything else returns the path itself.
        def hasher(path):
            if path in ("gfx/a.dds", "gfx/b.dds", "gfx/c.dds"):
                return "md5:identical"
            return f"path:{path}"
        report = srv._find_duplicate_images(allowlist={}, hasher=hasher)
        self.assertEqual(report["summary"]["flagged"], 1)
        cluster = report["flagged"][0]
        self.assertEqual(cluster["kind"], "content")
        self.assertEqual(sorted(cluster["images"]),
                         ["gfx/a.dds", "gfx/b.dds", "gfx/c.dds"])
        self.assertEqual(sorted(cluster["entities"]),
                         ["building_a", "building_b", "building_c"])

    def test_distinct_content_produces_no_findings(self):
        # Three buildings, three distinct paths, all distinct content.
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/a.dds"),
            "building_b": _entity(icon="gfx/b.dds"),
            "building_c": _entity(icon="gfx/c.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        # Default hasher: returns sentinel keyed by path → all distinct.
        def hasher(path):
            return f"path:{path}"
        report = srv._find_duplicate_images(allowlist={}, hasher=hasher)
        self.assertEqual(report["summary"]["flagged"], 0)

    def test_path_dupe_and_content_dupe_in_same_cluster(self):
        # Two buildings share path P; a third building has different path Q
        # but identical content. All three should be one cluster.
        mod = {"Buildings": {
            "building_a": _entity(icon="P.dds"),
            "building_b": _entity(icon="P.dds"),
            "building_c": _entity(icon="Q.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        def hasher(path):
            return "md5:same" if path in ("P.dds", "Q.dds") else f"path:{path}"
        report = srv._find_duplicate_images(allowlist={}, hasher=hasher)
        self.assertEqual(report["summary"]["flagged"], 1)
        cluster = report["flagged"][0]
        self.assertEqual(cluster["kind"], "content")  # multi-path → content
        self.assertEqual(sorted(cluster["entities"]),
                         ["building_a", "building_b", "building_c"])
        self.assertEqual(sorted(cluster["images"]), ["P.dds", "Q.dds"])

    def test_missing_file_falls_back_to_path_identity(self):
        # If hasher returns a path-sentinel (file missing on disk), entities
        # using different paths must NOT cluster — fall back to path identity.
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/missing_a.dds"),
            "building_b": _entity(icon="gfx/missing_b.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        def hasher(path):
            return f"path:{path}"  # both files missing → distinct sentinels
        report = srv._find_duplicate_images(allowlist={}, hasher=hasher)
        self.assertEqual(report["summary"]["flagged"], 0)


# ---------------------------------------------------------------------------
# Allowlist behavior
# ---------------------------------------------------------------------------
class AllowlistTests(unittest.TestCase):
    def setUp(self):
        self.original_ms = None

    def tearDown(self):
        if self.original_ms is not None:
            srv.ms = self.original_ms

    def test_exact_match_moves_to_allowlisted(self):
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/icons/shared.dds"),
            "building_b": _entity(icon="gfx/icons/shared.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        allowlist = {"Buildings": {
            (frozenset({"gfx/icons/shared.dds"}),
             frozenset({"building_a", "building_b"})): "shared by design",
        }}
        report = srv._find_duplicate_images(allowlist=allowlist, include_allowlisted=True)
        self.assertEqual(report["summary"]["flagged"], 0)
        self.assertEqual(report["summary"]["allowlisted"], 1)
        self.assertEqual(report["allowlisted"][0]["images"], ["gfx/icons/shared.dds"])
        self.assertEqual(report["allowlisted"][0]["reason"], "shared by design")

    def test_superset_re_flags(self):
        # Allowlist entry says only building_a + building_b may share. A third
        # joiner re-flags the whole cluster.
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/icons/shared.dds"),
            "building_b": _entity(icon="gfx/icons/shared.dds"),
            "building_c": _entity(icon="gfx/icons/shared.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        allowlist = {"Buildings": {
            (frozenset({"gfx/icons/shared.dds"}),
             frozenset({"building_a", "building_b"})): "old reason",
        }}
        report = srv._find_duplicate_images(allowlist=allowlist)
        self.assertEqual(report["summary"]["flagged"], 1)
        self.assertEqual(sorted(report["flagged"][0]["entities"]),
                         ["building_a", "building_b", "building_c"])

    def test_subset_re_flags(self):
        # Allowlist entry says a, b, c may share. If only a and b actually share
        # the entity sets don't match → re-flag (forces author to update entry).
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/icons/shared.dds"),
            "building_b": _entity(icon="gfx/icons/shared.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        allowlist = {"Buildings": {
            (frozenset({"gfx/icons/shared.dds"}),
             frozenset({"building_a", "building_b", "building_c"})):
                "all three were intended",
        }}
        report = srv._find_duplicate_images(allowlist=allowlist)
        self.assertEqual(report["summary"]["flagged"], 1)

    def test_content_dupe_allowlist_match(self):
        # A content cluster (multiple paths, same hash) can be allowlisted by
        # the (frozenset(paths), frozenset(entities)) key.
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/a.dds"),
            "building_b": _entity(icon="gfx/b.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        def hasher(path):
            return "md5:same" if path in ("gfx/a.dds", "gfx/b.dds") else f"path:{path}"
        allowlist = {"Buildings": {
            (frozenset({"gfx/a.dds", "gfx/b.dds"}),
             frozenset({"building_a", "building_b"})): "intentionally identical art",
        }}
        report = srv._find_duplicate_images(allowlist=allowlist, hasher=hasher,
                                            include_allowlisted=True)
        self.assertEqual(report["summary"]["flagged"], 0)
        self.assertEqual(report["summary"]["allowlisted"], 1)

    def test_allowlisted_omitted_unless_requested(self):
        mod = {"Buildings": {
            "building_a": _entity(icon="gfx/icons/shared.dds"),
            "building_b": _entity(icon="gfx/icons/shared.dds"),
        }}
        self.original_ms = _install_fake_ms(mod)
        allowlist = {"Buildings": {
            (frozenset({"gfx/icons/shared.dds"}),
             frozenset({"building_a", "building_b"})): "ok",
        }}
        report = srv._find_duplicate_images(allowlist=allowlist)
        # include_allowlisted defaults to False — the array should be absent or empty.
        self.assertNotIn("allowlisted", report)
        self.assertEqual(report["summary"]["allowlisted"], 1)


# ---------------------------------------------------------------------------
# Mod-only vs include-vanilla
# ---------------------------------------------------------------------------
class ModOnlyFilterTests(unittest.TestCase):
    def setUp(self):
        self.original_ms = None

    def tearDown(self):
        if self.original_ms is not None:
            srv.ms = self.original_ms

    def test_purely_vanilla_cluster_excluded_by_default(self):
        # Two vanilla buildings sharing an icon, no mod participation.
        # Default mode (mod-only) should NOT flag this.
        vanilla_buildings = {
            "vanilla_a": _entity(icon="gfx/icons/v_shared.dds"),
            "vanilla_b": _entity(icon="gfx/icons/v_shared.dds"),
        }
        # mod_parsers contains everything (vanilla + mod merged); base_parsers is vanilla-only.
        mod = {"Buildings": dict(vanilla_buildings)}
        base = {"Buildings": dict(vanilla_buildings)}
        self.original_ms = _install_fake_ms(mod, base=base)
        report = srv._find_duplicate_images(allowlist={})
        self.assertEqual(report["summary"]["flagged"], 0)

    def test_mod_entity_reusing_vanilla_image_is_flagged(self):
        # A mod building reusing the same icon as a vanilla building → flag.
        # The cluster contains both the vanilla and mod entities.
        mod = {"Buildings": {
            "vanilla_a": _entity(icon="gfx/icons/v.dds"),
            "mod_a": _entity(icon="gfx/icons/v.dds"),
        }}
        base = {"Buildings": {
            "vanilla_a": _entity(icon="gfx/icons/v.dds"),
        }}
        self.original_ms = _install_fake_ms(mod, base=base)
        report = srv._find_duplicate_images(allowlist={})
        self.assertEqual(report["summary"]["flagged"], 1)
        self.assertEqual(sorted(report["flagged"][0]["entities"]),
                         ["mod_a", "vanilla_a"])

    def test_include_vanilla_flag_shows_pure_vanilla_clusters(self):
        vanilla_buildings = {
            "vanilla_a": _entity(icon="gfx/icons/v_shared.dds"),
            "vanilla_b": _entity(icon="gfx/icons/v_shared.dds"),
        }
        mod = {"Buildings": dict(vanilla_buildings)}
        base = {"Buildings": dict(vanilla_buildings)}
        self.original_ms = _install_fake_ms(mod, base=base)
        report = srv._find_duplicate_images(allowlist={}, include_vanilla=True)
        self.assertEqual(report["summary"]["flagged"], 1)


# ---------------------------------------------------------------------------
# Allowlist YAML loader (tests the file-IO helper, not the report builder)
# ---------------------------------------------------------------------------
class AllowlistLoaderTests(unittest.TestCase):
    def test_loads_yaml_into_internal_shape(self):
        import tempfile
        import textwrap
        yaml_text = textwrap.dedent("""\
            buildings:
              - image: gfx/foo.dds
                entities: [building_a, building_b]
                reason: shared admin icon
              - images: [gfx/x.dds, gfx/y.dds]
                entities: [building_c, building_d]
                reason: identical art
            laws:
              - image: gfx/law.dds
                entities: [law_x, law_y]
                reason: tenant farmers reuse
            """)
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(yaml_text)
            path = f.name
        try:
            allowlist = srv._load_image_allowlist(path)
        finally:
            os.unlink(path)
        # Top-level YAML keys are lowercase entity-type slugs; loader must map them
        # to the canonical entity-type names ("Buildings", "Laws") used elsewhere.
        self.assertIn("Buildings", allowlist)
        self.assertIn("Laws", allowlist)
        bldg_entries = allowlist["Buildings"]
        # Singular `image:` form normalizes to a one-element frozenset.
        path_key = (frozenset({"gfx/foo.dds"}),
                    frozenset({"building_a", "building_b"}))
        self.assertIn(path_key, bldg_entries)
        self.assertEqual(bldg_entries[path_key], "shared admin icon")
        # Plural `images:` form keeps the full set.
        content_key = (frozenset({"gfx/x.dds", "gfx/y.dds"}),
                       frozenset({"building_c", "building_d"}))
        self.assertIn(content_key, bldg_entries)
        self.assertEqual(bldg_entries[content_key], "identical art")

    def test_missing_file_returns_empty(self):
        allowlist = srv._load_image_allowlist("/nonexistent/path/to/allowlist.yml")
        self.assertEqual(allowlist, {})


# ---------------------------------------------------------------------------
# Vanilla sanity test — runs the detector against a vanilla-only ModState and
# asserts each strict entity type produces at most a small handful of flagged
# clusters. If this blows up to thousands, we're aiming the tool at the wrong
# fields. Skipped by default because loading vanilla takes ~60s; opt in with
# VIC3_RUN_VANILLA_TESTS=1.
# ---------------------------------------------------------------------------
@unittest.skipUnless(
    os.environ.get("VIC3_RUN_VANILLA_TESTS") == "1",
    "Set VIC3_RUN_VANILLA_TESTS=1 to run the vanilla sanity test (~60s).",
)
class VanillaSanityTest(unittest.TestCase):
    """Vanilla itself should not produce many duplicate-image flags in the
    strict types. A few intentional reuses (e.g. tenant_farmers.dds across
    two agrarian laws) are tolerated; thousands means the tool is broken."""

    THRESHOLD_PER_TYPE = 10

    @classmethod
    def setUpClass(cls):
        # Build a minimal vanilla-only ModState restricted to the entity types
        # we scan for duplicates. Pass empty mod dict so mod_parsers == vanilla.
        from mod_state import ModState
        base_dirs = {
            etype: srv.base_game_paths[etype]
            for etype, _ in srv._IMAGE_FIELDS_BY_TYPE
            if etype in srv.base_game_paths
        }
        if not all(os.path.isdir(p) for p in base_dirs.values()):
            raise unittest.SkipTest("Vanilla install not found at base_game_path")
        cls._original_ms = srv.ms
        srv.ms = ModState(base_dirs, {})

    @classmethod
    def tearDownClass(cls):
        srv.ms = cls._original_ms

    def test_vanilla_strict_types_under_threshold(self):
        report = srv._find_duplicate_images(
            allowlist={},  # ignore any seeded allowlist for the raw count
            include_vanilla=True,
            include_allowlisted=True,
        )
        per_type: dict[str, int] = {}
        for cluster in report["flagged"]:
            per_type[cluster["entity_type"]] = per_type.get(cluster["entity_type"], 0) + 1
        for etype, count in per_type.items():
            self.assertLess(
                count, self.THRESHOLD_PER_TYPE,
                f"Vanilla scan produced {count} flagged image clusters for "
                f"{etype} — over threshold ({self.THRESHOLD_PER_TYPE}). "
                f"This usually means the tool is reading the wrong field for "
                f"this entity type. Full report: {per_type}"
            )


if __name__ == "__main__":
    unittest.main()
