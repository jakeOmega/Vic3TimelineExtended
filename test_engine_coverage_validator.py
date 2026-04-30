"""Unit + integration tests for /validate/engine-coverage.

Covers the boolean-modifier and `modifier:NAME` trigger validation paths
added after the country_sr_*_program_bool regression of 2026-04-29, where
the original validator silently ignored boolean references because its
suffix regex matched only `_add` / `_mult` / `_max_level(s)` / `_set`.

Pure unit tests (1–5) run in milliseconds against a synthetic ModState
fixture — no full vanilla parse needed. Integration test (6) hits the
running mod_state_server and is skipped if it isn't up.

Run:
    .venv/bin/python -m unittest test_engine_coverage_validator -v
"""

import json
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import mod_state_server as mss


SERVER = "http://127.0.0.1:8950"


class _MockParser:
    """Stand-in for the parser objects in ms.mod_parsers."""

    def __init__(self, data):
        self.data = data


class _MockModState:
    """Minimal ModState surface that _validate_engine_coverage touches."""

    def __init__(self, mod_parsers, modifier_types, script_values):
        self.mod_parsers = mod_parsers
        self._data = {
            "Modifier Types": modifier_types,
            "Script Values": script_values,
        }

    def get_data(self, etype):
        return self._data.get(etype, {})


def _build_fixture():
    """Synthetic mod state exercising every code path the validator must cover.

    Returns (mock_ms, fake_engine_docs) with:
      - PM `pm_test` referencing two booleans + two _add modifiers
      - JE `je_test` with a `possible` clause reading modifier:NAME for both bools
      - `Modifier Types` declaring foo_known_bool only
      - engine_docs declaring foo_known_add only
    """
    pm_data = {
        "country_modifiers": {
            "unscaled": {
                "foo_known_bool": "yes",
                "foo_unknown_bool": "yes",
                "foo_known_add": 5,
                "foo_unknown_add": 3,
            }
        }
    }
    je_data = {
        "possible": {
            "modifier:foo_known_bool": "yes",
            "modifier:foo_unknown_bool": "yes",
        }
    }
    mod_parsers = {
        "Production Methods": _MockParser({"pm_test": pm_data}),
        "Journal Entries": _MockParser({"je_test": je_data}),
    }
    modifier_types = {
        "foo_known_bool": {"color": "good", "boolean": "yes"},
    }
    fake_ms = _MockModState(mod_parsers, modifier_types, script_values={})
    fake_engine_docs = {"modifiers": [{"name": "foo_known_add"}]}
    return fake_ms, fake_engine_docs


class ValidatorBooleanCoverageTests(unittest.TestCase):
    """Pure unit tests against a synthetic ModState — no server needed."""

    def setUp(self):
        self.fake_ms, self.fake_engine_docs = _build_fixture()
        # Patch module globals the validator reads.
        self._patches = [
            patch.object(mss, "ms", self.fake_ms),
            patch.object(mss, "engine_docs", self.fake_engine_docs),
            patch.object(mss, "pattern_catalog", []),
            patch.object(mss, "modifier_to_pattern", {}),
            # Vocabulary index would require a real ModState; the validator
            # only consults it via pattern_pairs, which is empty here.
            patch.object(mss, "_vocabulary_index", return_value={}),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()

    def _names(self, bucket_key):
        report = mss._validate_engine_coverage()
        return {e["name"] for e in report.get(bucket_key, [])}

    def test_known_boolean_in_pm_not_flagged(self):
        """foo_known_bool is declared in Modifier Types → not in unknown."""
        self.assertNotIn("foo_known_bool", self._names("unknown_modifiers"))
        self.assertNotIn("foo_known_bool", self._names("suspicious_modifiers"))

    def test_unknown_boolean_in_pm_flagged(self):
        """foo_unknown_bool referenced by PM but not declared → flagged."""
        unknown = self._names("unknown_modifiers")
        self.assertIn(
            "foo_unknown_bool", unknown,
            f"Expected foo_unknown_bool in unknown_modifiers, got: {sorted(unknown)}",
        )

    def test_modifier_trigger_known_not_flagged(self):
        """modifier:foo_known_bool = yes in JE possible → not flagged."""
        self.assertNotIn("foo_known_bool", self._names("unknown_modifiers"))

    def test_modifier_trigger_unknown_flagged_with_je_path(self):
        """modifier:foo_unknown_bool = yes in JE possible → flagged with JE path."""
        report = mss._validate_engine_coverage()
        unknown = {e["name"]: e for e in report.get("unknown_modifiers", [])}
        self.assertIn("foo_unknown_bool", unknown)
        used_in = unknown["foo_unknown_bool"]["used_in"]
        # At least one citation must come from the JE possible-clause path.
        self.assertTrue(
            any("Journal Entries/je_test" in p for p in used_in),
            f"Expected JE path in used_in, got: {used_in}",
        )

    def test_existing_add_path_still_works(self):
        """Regression: the pre-existing _add suffix path keeps working."""
        unknown = self._names("unknown_modifiers")
        self.assertIn("foo_unknown_add", unknown)
        self.assertNotIn("foo_known_add", unknown)


def _server_running() -> bool:
    try:
        with urllib.request.urlopen(f"{SERVER}/status", timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


class CountrySpaceRaceRegressionIntegration(unittest.TestCase):
    """Regression test against the live server, freezing the country_sr_* bug.

    With the definitions present in tech_gate_modifier_types.txt the engine-
    coverage report contains zero country_sr_*_program_bool entries. If a
    future commit deletes those definitions, both PM references and JE
    `possible` triggers will surface as unknown — exactly the signal the
    validator was missing on 2026-04-29.

    Skipped when the server is not running.
    """

    @unittest.skipUnless(_server_running(), "mod_state_server not running on :8950")
    def test_country_sr_program_bools_resolve_when_defined(self):
        with urllib.request.urlopen(f"{SERVER}/validate/engine-coverage") as r:
            report = json.loads(r.read())
        unknown_names = {e["name"] for e in report.get("unknown_modifiers", [])}
        suspicious_names = {e["name"] for e in report.get("suspicious_modifiers", [])}
        sr_unknown = sorted(n for n in unknown_names if n.startswith("country_sr_"))
        sr_suspicious = sorted(n for n in suspicious_names if n.startswith("country_sr_"))
        self.assertEqual(
            sr_unknown, [],
            f"country_sr_* booleans should resolve once defined, got unknown: {sr_unknown}"
        )
        self.assertEqual(
            sr_suspicious, [],
            f"country_sr_* booleans should resolve once defined, got suspicious: {sr_suspicious}"
        )


if __name__ == "__main__":
    unittest.main()
