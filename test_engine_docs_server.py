"""Tests for mod_state_server engine-docs upgrades:
- `_parse_effects_triggers_log` parser: extracts example/traits/reads fields
  out of the markdown-styled docs (previously these all landed in description).
- `_engine_docs_find_usage`: filters vanilla `common/` for call-site usages,
  excludes definitions and trigger-localization labels by default.
- `_load_engine_docs` leaves the committed docs/engine/ files alone when the
  engine logs are incomplete or older than the ones they were rendered from.

Both are tested by direct module import rather than via the HTTP server (the
server takes ~90s to warm up; the underlying functions are pure-Python and
testable in isolation).
"""
import os
import tempfile
import unittest
from unittest import mock

import mod_state_server as mss


# Sample trigger doc lines mirroring the vanilla format (## name / description
# prose / usage example / Traits / Reads gamestate / Supported Scopes).
_SAMPLE_TRIGGERS_LOG = """# Trigger Documentation
## active_lens
Checks if the specified lens is open
active_lens = lens
**Supported Scopes**: none

## global_country_ranking
Compares a Country's Power Ranking (position)
global_country_ranking > 42
Traits: <, <=, =, !=, >, >=
Reads gamestate for all scopes.
**Supported Scopes**: country

## is_in_geographic_region
Checks if a scoped object is in a specific geographic region
is_in_geographic_region = geographic_region:geographic_region_africa
Reads gamestate for all scopes.
**Supported Scopes**: country, state, state_region, strategic_region

## amendment_stance
Compares the stance of the scoped character, movement or interest group has on the specified amendment type, assuming the amendment type has a parent law
amendment_stance = {
\tamendment = <scope>
\tvalue = <stance>
}
Reads gamestate for all scopes.
**Supported Scopes**: character, interest_group, political_movement

## any_active_law
Iterate through all active laws in a country
any_active_law = { <count=num/all> / <percent=fixed_point> <triggers> }
Reads nothing for all scopes.
**Supported Scopes**: country
**Supported Targets**: law
"""


class ParserFieldExtractionTests(unittest.TestCase):
    """Verify the upgraded parser splits description / example / traits / reads
    correctly. Before the upgrade everything beneath `## name` was lumped into
    description and `/engine-docs/origin/<name>` had nothing meaningful to
    surface."""

    @classmethod
    def setUpClass(cls):
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
            f.write(_SAMPLE_TRIGGERS_LOG)
            cls.path = f.name
        cls.entries = {e["name"]: e for e in mss._parse_effects_triggers_log(cls.path)}

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.path)

    def test_minimal_entry_has_example_and_no_traits(self):
        e = self.entries["active_lens"]
        self.assertEqual(e["example"], "active_lens = lens")
        self.assertEqual(e["traits"], "")
        self.assertEqual(e["reads"], "")
        self.assertEqual(e["scopes"], ["none"])

    def test_value_comparison_trigger_has_traits_and_reads(self):
        e = self.entries["global_country_ranking"]
        self.assertEqual(e["example"], "global_country_ranking > 42")
        self.assertEqual(e["traits"], "<, <=, =, !=, >, >=")
        self.assertEqual(e["reads"], "Reads gamestate for all scopes.")
        self.assertEqual(e["scopes"], ["country"])
        self.assertEqual(e["description"], "Compares a Country's Power Ranking (position)")

    def test_geographic_region_trigger_clean_split(self):
        e = self.entries["is_in_geographic_region"]
        self.assertEqual(
            e["example"],
            "is_in_geographic_region = geographic_region:geographic_region_africa",
        )
        self.assertIn("country", e["scopes"])
        self.assertIn("state", e["scopes"])
        self.assertIn("strategic_region", e["scopes"])
        # Description should be the prose only, not the example/reads.
        self.assertEqual(
            e["description"],
            "Checks if a scoped object is in a specific geographic region",
        )

    def test_multiline_example_opens_at_first_brace_line(self):
        # When an entry opens a multi-line example block (`name = {` followed by
        # body lines), the first line wins as `example`; continuation lines
        # remain in description so they aren't lost.
        e = self.entries["amendment_stance"]
        self.assertTrue(e["example"].startswith("amendment_stance = {"))
        self.assertIn("amendment = <scope>", e["description"])

    def test_iterator_targets(self):
        e = self.entries["any_active_law"]
        self.assertEqual(e["targets"], ["law"])
        self.assertEqual(e["reads"], "Reads nothing for all scopes.")


class FindUsageFilterTests(unittest.TestCase):
    """Verify call-site filtering. These hit vanilla `common/` so they're
    integration-flavored — skip when the vanilla path isn't present (CI)."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(mss._BASE_COMMON):
            raise unittest.SkipTest(f"Vanilla common dir not found: {mss._BASE_COMMON}")

    def test_returns_call_sites_for_documented_trigger(self):
        # is_in_geographic_region is well-documented and widely used in vanilla
        # — must return at least a couple of usage snippets with file:line.
        r = mss._engine_docs_find_usage("is_in_geographic_region", limit=3)
        self.assertGreater(r["returned"], 0)
        self.assertIn(r["backend"], ("grep", "ripgrep", "python"))
        for u in r["uses"]:
            self.assertIn("file", u)
            self.assertIn("line", u)
            self.assertIn("snippet", u)
            # Snippets should mark the matched line with `>`.
            self.assertIn(">", u["snippet"])

    def test_returns_call_sites_for_undocumented_trigger(self):
        # has_treaty_defensive_pact_with is NOT in triggers.log but IS used in
        # vanilla — this case is the primary motivation for the usage endpoint.
        r = mss._engine_docs_find_usage("has_treaty_defensive_pact_with", limit=3)
        self.assertGreater(r["returned"], 0, "Expected at least one usage of has_treaty_defensive_pact_with in vanilla common/")

    def test_default_filter_skips_column_zero_definition(self):
        # `has_treaty_defensive_pact_with` is defined at column 0 inside
        # scripted_triggers/00_diplomacy_triggers.txt. Default-filtered results
        # must not include that line.
        r = mss._engine_docs_find_usage("has_treaty_defensive_pact_with", limit=10)
        for u in r["uses"]:
            self.assertFalse(
                u["file"].startswith("scripted_triggers/") and "trigger_definitions" not in u["file"]
                and u["snippet"].splitlines()[
                    next(i for i, ln in enumerate(u["snippet"].splitlines()) if ln.startswith(">"))
                ].split(":", 1)[1].lstrip().startswith("has_treaty_defensive_pact_with "),
                f"Default filter should exclude column-0 definition: {u}",
            )

    def test_include_defs_keeps_everything(self):
        # With include_defs=True, the scripted_triggers definition site appears.
        r = mss._engine_docs_find_usage(
            "has_treaty_defensive_pact_with", limit=10, include_defs=True
        )
        files = {u["file"] for u in r["uses"]}
        self.assertTrue(
            any("scripted_triggers/" in f for f in files),
            f"include_defs=True should include scripted_triggers definition; got {files}",
        )

    def test_filter_excludes_trigger_localization_by_default(self):
        # has_treaty_defensive_pact_with_trigger appears in trigger_localization/
        # as a display-label cross-reference, not a script call. Filter it out.
        r = mss._engine_docs_find_usage("has_treaty_defensive_pact_with", limit=10)
        for u in r["uses"]:
            self.assertFalse(
                u["file"].startswith("trigger_localization" + os.sep),
                f"trigger_localization match should be filtered: {u}",
            )

    def test_unknown_name_returns_zero_uses(self):
        r = mss._engine_docs_find_usage("nonexistent_phantom_trigger_xyz", limit=5)
        self.assertEqual(r["returned"], 0)
        self.assertEqual(r["uses"], [])

    def test_invalid_identifier_rejected(self):
        r = mss._engine_docs_find_usage("not a valid name", limit=5)
        self.assertIn("error", r)
        self.assertEqual(r["uses"], [])


class OriginHandlerSchemaTests(unittest.TestCase):
    """Verify /engine-docs/origin/<name> surfaces the full schema (the original
    handler dropped description/example/scopes — making the endpoint return
    nearly empty matches even when the trigger was documented)."""

    def setUp(self):
        # Replace the module-global engine_docs with a small fixture so we don't
        # depend on a loaded server. Restore after each test.
        self._original = mss.engine_docs
        mss.engine_docs = {
            "triggers": [
                {
                    "name": "is_in_geographic_region",
                    "origin": "vanilla",
                    "description": "Checks if a scoped object is in a specific geographic region",
                    "example": "is_in_geographic_region = geographic_region:geographic_region_africa",
                    "traits": "",
                    "reads": "Reads gamestate for all scopes.",
                    "scopes": ["country", "state", "state_region", "strategic_region"],
                    "targets": [],
                },
            ],
            "modifiers": [
                {
                    "name": "country_authority_add",
                    "origin": "vanilla",
                    "mask": "country",
                    "display_name": "Authority",
                    "description": "",
                },
            ],
        }

    def tearDown(self):
        mss.engine_docs = self._original

    def _call_origin(self, name: str) -> dict:
        # Instantiate the handler class to call the method. _engine_docs is a
        # bound method on the request-handler class; create one without going
        # through HTTP.
        # Simpler: reach the method via the class and pass a stub self.
        cls = mss.ModStateHandler
        return cls._engine_docs(self=None, parts=["origin", name], params={})

    def test_origin_surfaces_full_trigger_schema(self):
        r = self._call_origin("is_in_geographic_region")
        self.assertTrue(r["found"])
        self.assertEqual(len(r["matches"]), 1)
        m = r["matches"][0]
        self.assertEqual(m["type"], "triggers")
        self.assertEqual(m["origin"], "vanilla")
        self.assertEqual(
            m["description"],
            "Checks if a scoped object is in a specific geographic region",
        )
        self.assertEqual(
            m["example"],
            "is_in_geographic_region = geographic_region:geographic_region_africa",
        )
        self.assertEqual(m["reads"], "Reads gamestate for all scopes.")
        self.assertIn("country", m["scopes"])

    def test_origin_surfaces_modifier_specific_fields(self):
        r = self._call_origin("country_authority_add")
        self.assertTrue(r["found"])
        m = r["matches"][0]
        self.assertEqual(m["mask"], "country")
        self.assertEqual(m["display_name"], "Authority")
        # Empty/missing optional fields should not appear.
        self.assertNotIn("description", m)
        self.assertNotIn("traits", m)

    def test_origin_unknown_name_returns_empty_matches(self):
        r = self._call_origin("phantom_xyz")
        self.assertFalse(r["found"])
        self.assertEqual(r["matches"], [])


class TypeKeyAndListingTests(unittest.TestCase):
    """#326 — /engine-docs/<type>/<name> returns that entry (it used to return
    the whole unfiltered listing), and the listing says when it was capped."""

    def setUp(self):
        self._original = mss.engine_docs
        mss.engine_docs = {
            "triggers": [
                {"name": "active_lens", "origin": "vanilla", "scopes": ["none"]},
                {"name": "primary_cultures_percent_country", "origin": "vanilla",
                 "example": "primary_cultures_percent_country >= 0.5",
                 "scopes": ["country"]},
                {"name": "primary_cultures_percent_state", "origin": "vanilla",
                 "scopes": ["state"]},
            ],
            "event-targets": [
                {"name": "num_active_ships", "input_scopes": ["country"]},
                {"name": "num_active_ships", "input_scopes": ["military_formation"]},
            ],
            "modifiers": [
                {"name": "country_authority_add", "origin": "vanilla", "decimals": 0},
            ],
        }

    def tearDown(self):
        mss.engine_docs = self._original

    def _call(self, parts, params=None):
        return mss.ModStateHandler._engine_docs(self=None, parts=parts, params=params or {})

    def test_key_returns_that_entry_only(self):
        r = self._call(["triggers", "primary_cultures_percent_country"])
        self.assertTrue(r["found"])
        self.assertEqual(r["type"], "triggers")
        self.assertEqual(len(r["matches"]), 1)
        # The full entry, not origin's field subset.
        self.assertEqual(r["matches"][0]["example"], "primary_cultures_percent_country >= 0.5")
        r = self._call(["modifiers", "country_authority_add"])
        self.assertEqual(r["matches"][0]["decimals"], 0)

    def test_key_keeps_repeated_names(self):
        r = self._call(["event-targets", "num_active_ships"])
        self.assertEqual(len(r["matches"]), 2)

    def test_unknown_key_is_404_with_close_matches(self):
        with self.assertRaises(mss.NotFound) as ctx:
            self._call(["triggers", "primary_cultures_percent_countr"])
        self.assertEqual(ctx.exception.status, 404)
        self.assertIn("primary_cultures_percent_country", ctx.exception.payload["did_you_mean"])

    def test_key_in_the_wrong_type_names_the_right_one(self):
        with self.assertRaises(mss.NotFound) as ctx:
            self._call(["triggers", "country_authority_add"])
        self.assertEqual(ctx.exception.payload["defined_in_types"], ["modifiers"])

    def test_extra_segment_is_400(self):
        with self.assertRaises(mss.BadRequest) as ctx:
            self._call(["triggers", "active_lens", "extra"])
        self.assertEqual(ctx.exception.status, 400)

    def test_listing_reports_truncation(self):
        r = self._call(["triggers"], {"limit": ["1"]})
        self.assertEqual(r["count"], 3)
        self.assertEqual(r["returned"], 1)
        self.assertTrue(r["truncated"])
        self.assertEqual(len(r["entries"]), 1)

    def test_listing_untruncated(self):
        r = self._call(["triggers"], {"q": ["primary_cultures"]})
        self.assertEqual(r["count"], 2)
        self.assertEqual(r["returned"], 2)
        self.assertFalse(r["truncated"])

    def test_unknown_type_still_404(self):
        with self.assertRaises(mss.NotFound):
            self._call(["no-such-type"])


class LocFunctionIndexTests(unittest.TestCase):
    """Verify the loc-function index discovers canonical data-system functions
    from vanilla loc + GUI files. Integration-flavored: skip when vanilla
    isn't present."""

    @classmethod
    def setUpClass(cls):
        loc_root = os.path.join(mss.base_game_path, "game", "localization", "english")
        if not os.path.isdir(loc_root):
            raise unittest.SkipTest(f"Vanilla loc dir not found: {loc_root}")
        # Force a fresh index for this test class.
        mss._LOC_FUNCTION_INDEX = None
        cls.index = mss._get_loc_function_index()

    def test_canonical_functions_indexed(self):
        # Functions that I (the agent) had to discover by ad-hoc grep when
        # working on issue #31 — they should appear in the index with usage
        # counts consistent with vanilla.
        for name in (
            "GetStaticModifier",
            "GetValueWithBreakdownFor",
            "GetNameNoFormatting",
            "Concept",
            "AddTextIf",
        ):
            self.assertIn(name, self.index, f"Expected {name} in loc-function index")
            self.assertGreater(self.index[name]["count"], 0)
            self.assertGreater(len(self.index[name]["examples"]), 0)

    def test_kind_classification(self):
        # GetStaticModifier appears at expression start (e.g. [GetStaticModifier('X').GetDesc])
        # — classified as `function`.
        self.assertEqual(self.index["GetStaticModifier"]["kind"], "function")
        # GetValueWithBreakdownFor is always called after a dot — classified as `method`.
        self.assertEqual(self.index["GetValueWithBreakdownFor"]["kind"], "method")
        # ROOT is all-uppercase — classified as `scope`.
        self.assertEqual(self.index["ROOT"]["kind"], "scope")
        # sCharacter starts lowercase, has CamelCase tail — classified as `accessor`.
        self.assertEqual(self.index["sCharacter"]["kind"], "accessor")

    def test_lowercase_only_idents_excluded(self):
        # Tokens like `concept_pop` are entity references, not functions — they
        # should not appear in the function-like index.
        self.assertNotIn("concept_pop", self.index)
        self.assertNotIn("concept_homeland", self.index)

    def test_examples_carry_file_and_line(self):
        for ex in self.index["GetStaticModifier"]["examples"]:
            self.assertIn("file", ex)
            self.assertIn("line", ex)
            self.assertIn("expression", ex)
            # The expression is the full `[...]` substring.
            self.assertTrue(ex["expression"].startswith("["))
            self.assertTrue(ex["expression"].endswith("]"))


class LocFunctionEndpointTests(unittest.TestCase):
    """Verify the /engine-docs/loc-functions endpoint surfaces the index."""

    @classmethod
    def setUpClass(cls):
        loc_root = os.path.join(mss.base_game_path, "game", "localization", "english")
        if not os.path.isdir(loc_root):
            raise unittest.SkipTest(f"Vanilla loc dir not found: {loc_root}")
        # Reuse the cached index from the previous class if present.
        mss._get_loc_function_index()

    def _call(self, parts, params=None):
        cls = mss.ModStateHandler
        return cls._engine_docs(self=None, parts=parts, params=params or {})

    def test_listing_sorted_by_count_desc(self):
        r = self._call(["loc-functions"], {"limit": ["5"]})
        self.assertIn("entries", r)
        self.assertEqual(r["returned"], 5)
        counts = [e["count"] for e in r["entries"]]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_listing_q_filter(self):
        r = self._call(["loc-functions"], {"q": ["StaticModifier"], "limit": ["20"]})
        for e in r["entries"]:
            self.assertIn("staticmodifier", e["name"].lower())
        # GetStaticModifier should be in the filtered set.
        names = {e["name"] for e in r["entries"]}
        self.assertIn("GetStaticModifier", names)

    def test_listing_kind_filter(self):
        r = self._call(["loc-functions"], {"kind": ["scope"], "limit": ["10"]})
        for e in r["entries"]:
            self.assertEqual(e["kind"], "scope")

    def test_single_function_returns_examples(self):
        r = self._call(["loc-functions", "GetStaticModifier"], {"limit": ["3"]})
        self.assertTrue(r["found"])
        self.assertEqual(r["name"], "GetStaticModifier")
        self.assertEqual(r["kind"], "function")
        self.assertLessEqual(len(r["examples"]), 3)
        self.assertGreater(len(r["examples"]), 0)
        self.assertIn("expression", r["examples"][0])

    def test_unknown_function_returns_not_found(self):
        r = self._call(["loc-functions", "PhantomFunctionXyz"], {})
        self.assertFalse(r["found"])
        self.assertEqual(r["examples"], [])

    def test_min_count_filter(self):
        # GetNameNoFormatting has 1000+ uses; min_count=1000 should keep it.
        r = self._call(["loc-functions"], {"min_count": ["1000"], "limit": ["50"]})
        for e in r["entries"]:
            self.assertGreaterEqual(e["count"], 1000)


_ENGINE_LOGS = (
    "effects.log", "triggers.log", "modifiers.log",
    "event_targets.log", "on_actions.log", "custom_localization.log",
)


def _fake_log_parser(path: str) -> list[dict]:
    """One entry per non-empty log, none for an empty one."""
    return [{"name": os.path.basename(path)}] if os.path.getsize(path) else []


class EngineDocsRenderGuardTests(unittest.TestCase):
    """`_load_engine_docs` must not re-render docs/engine/ from missing, empty
    or older engine logs: in a game-less container that replaced ~30k committed
    lines with mod-only content, and the audits reading them changed verdicts."""

    COMMITTED = "# Auto-generated from modifiers.log (engine docs 1.14.5). Do not hand-edit.\ncommitted\n"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.engine_dir = os.path.join(self.root, "docs", "engine")
        os.makedirs(self.engine_dir)
        self.summary = os.path.join(self.engine_dir, "modifiers_summary.txt")
        with open(self.summary, "w", encoding="utf-8") as f:
            f.write(self.COMMITTED)
        self.render = mock.Mock(return_value={})
        self.source = (os.path.join(self.root, "missing"), "mod_loaded")
        patches = [
            mock.patch.object(mss, "doc_path", os.path.join(self.root, "docs")),
            mock.patch.object(mss, "_engine_docs_source", lambda: self.source),
            mock.patch("engine_docs_render.render_all", self.render),
            mock.patch("game_log_reader.render_error_log_digest", return_value=""),
            mock.patch.object(mss, "_build_pattern_data", return_value=([], {}, [], {})),
            mock.patch.object(mss, "_validate_engine_coverage", return_value={}),
            mock.patch.object(mss, "_annotate_validation_with_error_log"),
            mock.patch.object(mss, "_render_engine_coverage_md", return_value=""),
            # Module state _load_engine_docs rebinds; restored afterwards.
            mock.patch.object(mss, "engine_docs", {}),
            mock.patch.object(mss, "engine_docs_sources", {}),
            mock.patch.object(mss, "engine_docs_source_label", ""),
            mock.patch.object(mss, "_engine_docs_warnings", []),
            mock.patch.object(mss, "_last_validation_report", None),
        ]
        for name in ("_union_vanilla_modifier_decimals", "_union_mod_modifier_types",
                     "_union_mod_custom_localization", "_refresh_pattern_state"):
            patches.append(mock.patch.object(mss, name))
        for name in ("_parse_effects_triggers_log", "_parse_modifiers_log",
                     "_parse_event_targets_log", "_parse_on_actions_log",
                     "_parse_custom_localization_log"):
            patches.append(mock.patch.object(mss, name, _fake_log_parser))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _use_logs(self, version_dir: str, *, empty=(), absent=()) -> None:
        docs = os.path.join(self.root, "digests", version_dir, "docs")
        os.makedirs(docs)
        for name in _ENGINE_LOGS:
            if name in absent:
                continue
            with open(os.path.join(docs, name), "w", encoding="utf-8") as f:
                f.write("" if name in empty else "## entry\n")
        self.source = (docs, "digest_snapshot")

    def _assert_skipped(self) -> dict:
        self.render.assert_not_called()
        with open(self.summary, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.COMMITTED)
        self.assertEqual(len(mss._engine_docs_warnings), 1)
        warning = mss._engine_docs_warnings[0]
        self.assertEqual(warning["label"], "engine_docs_render_skipped")
        self.assertIn("not re-rendered", warning["detail"])
        return warning

    def test_no_engine_logs_skips_render(self):
        mss._load_engine_docs()
        warning = self._assert_skipped()
        self.assertEqual(warning["missing"], list(_ENGINE_LOGS))
        self.assertEqual(warning["source_label"], "mod_loaded")

    def test_one_missing_log_skips_render(self):
        self._use_logs("1.14.5", absent=("on_actions.log",))
        mss._load_engine_docs()
        self.assertEqual(self._assert_skipped()["missing"], ["on_actions.log"])

    def test_empty_log_skips_render(self):
        self._use_logs("1.14.5", empty=("custom_localization.log",))
        mss._load_engine_docs()
        self.assertEqual(self._assert_skipped()["missing"], ["custom_localization.log"])

    def test_older_snapshot_than_rendered_skips_render(self):
        self._use_logs("1.13.11")
        mss._load_engine_docs()
        warning = self._assert_skipped()
        self.assertNotIn("missing", warning)
        self.assertEqual(warning["source_version"], "1.13.11")
        self.assertEqual(warning["rendered_version"], "1.14.5")

    def test_complete_logs_render(self):
        for version in ("1.14.5", "1.14.10"):
            with self.subTest(version=version):
                self.render.reset_mock()
                self._use_logs(version)
                mss._load_engine_docs()
                self.render.assert_called_once()
                self.assertEqual(mss._engine_docs_warnings, [])

    def test_complete_logs_render_without_a_rendered_version(self):
        os.remove(self.summary)
        self._use_logs("1.13.11")
        mss._load_engine_docs()
        self.render.assert_called_once()

    def test_engine_only_reload_reports_the_skip(self):
        warnings = mss._reload_engine_only()
        self.assertEqual(
            [w["label"] for w in warnings], ["engine_docs_render_skipped"]
        )


if __name__ == "__main__":
    unittest.main()
