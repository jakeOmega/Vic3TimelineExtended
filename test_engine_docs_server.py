"""Tests for mod_state_server engine-docs upgrades:
- `_parse_effects_triggers_log` parser: extracts example/traits/reads fields
  out of the markdown-styled docs (previously these all landed in description).
- `_engine_docs_find_usage`: filters vanilla `common/` for call-site usages,
  excludes definitions and trigger-localization labels by default.

Both are tested by direct module import rather than via the HTTP server (the
server takes ~90s to warm up; the underlying functions are pure-Python and
testable in isolation).
"""
import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
