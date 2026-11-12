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

    def __init__(self, mod_parsers, modifier_types, script_values,
                 scripted_effects=None, scripted_triggers=None):
        self.mod_parsers = mod_parsers
        self._data = {
            "Modifier Types": modifier_types,
            "Script Values": script_values,
            "Scripted Effects": scripted_effects or {},
            "Scripted Triggers": scripted_triggers or {},
        }

    def get_data(self, etype):
        return self._data.get(etype, {})


def _build_fixture():
    """Synthetic mod state exercising every code path the validator must cover.

    Returns (mock_ms, fake_engine_docs) with:
      - PM `pm_test` referencing two booleans + two _add modifiers
      - JE `je_test` with a `possible` clause reading modifier:NAME for both bools
      - `Modifier Types` declaring foo_known_bool and foo_known_add
      - engine_docs (the `modifiers.log` dump) listing foo_listed_add, which
        no definition registers (#391)
    """
    pm_data = {
        "country_modifiers": {
            "unscaled": {
                "foo_known_bool": "yes",
                "foo_unknown_bool": "yes",
                "foo_known_add": 5,
                "foo_unknown_add": 3,
                "foo_listed_add": 2,
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
        "foo_known_add": {"color": "good"},
    }
    fake_ms = _MockModState(mod_parsers, modifier_types, script_values={})
    fake_engine_docs = {"modifiers": [{"name": "foo_listed_add"}]}
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

    def test_name_only_the_engine_docs_list_is_flagged(self):
        """#391 gap 1: `modifiers.log` listing a name does not register it.

        A dump older than the game still lists a name a patch removed (1.14.4's
        `country_prestige_from_navy_power_projection_mult`), and a current one
        lists every name the engine could register."""
        report = mss._validate_engine_coverage()
        unknown = {e["name"]: e for e in report["unknown_modifiers"]}
        self.assertIn("foo_listed_add", unknown)
        self.assertIs(unknown["foo_listed_add"].get("listed_in_engine_docs"), True)
        self.assertNotIn("listed_in_engine_docs", unknown["foo_unknown_add"])


_THROUGHPUT = "building_{building}_throughput_add"


def _build_pattern_fixture():
    """A production method granting four names of one dynamic family (#391 gap 2).

    The pattern catalog knows `building_{building}_throughput_add` and the
    building vocabulary holds three buildings. Only the biomass plant's type is
    defined; the coal plant's is the #681 case (a mod building, never
    registered); Angkor Wat's is one `modifiers.log` lists and vanilla does not
    register; the fourth names no building."""
    pms = {
        "pm_test": {
            "building_modifiers": ("=", {"workforce_scaled": ("=", {
                "building_synthetics_plant_biomass_throughput_add": ("=", "0.05"),
                "building_synthetics_plant_coal_throughput_add": ("=", "0.05"),
                "building_angkor_wat_throughput_add": ("=", "0.05"),
                "building_synthetic_plant_throughput_add": ("=", "0.05"),
            })}),
        },
    }
    jes = {
        "je_test": {
            "possible": ("=", {
                "modifier:building_synthetics_plant_coal_throughput_add": ("=", "0.05"),
            }),
        },
    }
    fake_ms = _MockModState(
        {"Production Methods": _MockParser(pms), "Journal Entries": _MockParser(jes)},
        modifier_types={"building_synthetics_plant_biomass_throughput_add": {"color": "good"}},
        script_values={},
    )
    catalog = [{"pattern": _THROUGHPUT, "placeholder": "building", "vocab": "building"}]
    vocab = {"building": ["synthetics_plant_biomass", "synthetics_plant_coal", "angkor_wat"]}
    listed = "building_angkor_wat_throughput_add"
    return (fake_ms, {"modifiers": [{"name": listed}]}, catalog, vocab,
            {listed: (_THROUGHPUT, "angkor_wat", "catalog")})


class ValidatorPatternRegistrationTests(unittest.TestCase):
    """#391 gap 2: a name that fits a dynamic pattern still needs its own definition."""

    def setUp(self):
        fake_ms, docs, catalog, vocab, to_pattern = _build_pattern_fixture()
        self._patches = [
            patch.object(mss, "ms", fake_ms),
            patch.object(mss, "engine_docs", docs),
            patch.object(mss, "pattern_catalog", catalog),
            patch.object(mss, "modifier_to_pattern", to_pattern),
            patch.object(mss, "_vocabulary_index", return_value=vocab),
        ]
        for p in self._patches:
            p.start()
        self.report = mss._validate_engine_coverage()
        self.unknown = {e["name"]: e for e in self.report["unknown_modifiers"]}
        self.suspicious = {e["name"]: e for e in self.report["suspicious_modifiers"]}

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()

    def test_registered_instance_is_clean(self):
        name = "building_synthetics_plant_biomass_throughput_add"
        self.assertNotIn(name, self.unknown)
        self.assertNotIn(name, self.suspicious)

    def test_unregistered_instance_of_a_known_building_is_flagged(self):
        """`carbon_removal_modifier`'s line (#681): the building exists, the type does not."""
        entry = self.unknown.get("building_synthetics_plant_coal_throughput_add")
        self.assertIsNotNone(entry, sorted(self.unknown))
        self.assertEqual(entry["pattern"], _THROUGHPUT)
        self.assertEqual(entry["value"], "synthetics_plant_coal")
        self.assertIs(entry["unregistered_pattern_instance"], True)
        self.assertNotIn("listed_in_engine_docs", entry)

    def test_modifier_read_of_an_unregistered_instance_is_flagged(self):
        used = self.unknown["building_synthetics_plant_coal_throughput_add"]["used_in"]
        self.assertTrue(any("Production Methods/pm_test" in u for u in used), used)
        self.assertTrue(any("modifier:building_synthetics_plant_coal_throughput_add" in u
                            for u in used), used)

    def test_instance_the_engine_docs_list_is_flagged(self):
        """`modifiers.log` lists a throughput type for every building; vanilla
        defines it for under half of them."""
        entry = self.unknown.get("building_angkor_wat_throughput_add")
        self.assertIsNotNone(entry, sorted(self.unknown))
        self.assertIs(entry["listed_in_engine_docs"], True)
        self.assertIs(entry["unregistered_pattern_instance"], True)
        self.assertEqual(entry["value"], "angkor_wat")

    def test_markdown_report_says_what_unknown_means_and_tags_each_name(self):
        """The rendered report states the rule (only a definition makes a name
        valid; the engine docs and the pattern catalog do not) and says on each
        line whether the dump lists the name and which family it fits."""
        md = mss._render_engine_coverage_md(self.report)
        section = md.split("## Unknown modifiers", 1)[1]
        self.assertIn("no modifier type definition registers", section)
        self.assertNotIn("absent from both", section)
        self.assertNotIn("regenerate the engine docs in-game", section)
        lines = {line.split("`")[1]: line for line in section.splitlines() if line.startswith("- `")}
        angkor = lines["building_angkor_wat_throughput_add"]
        self.assertIn("listed in the engine docs", angkor)
        self.assertIn(f"unregistered instance of `{_THROUGHPUT}` (`angkor_wat`)", angkor)
        coal = lines["building_synthetics_plant_coal_throughput_add"]
        self.assertIn("unregistered instance of", coal)
        self.assertNotIn("listed in the engine docs", coal)

    def test_value_outside_the_vocabulary_stays_suspicious(self):
        entry = self.suspicious.get("building_synthetic_plant_throughput_add")
        self.assertIsNotNone(entry, sorted(self.suspicious))
        self.assertEqual(entry["captured_value"], "synthetic_plant")
        self.assertNotIn("building_synthetic_plant_throughput_add", self.unknown)

    def test_classifier_never_answers_pattern(self):
        """No status but 'engine' clears a name."""
        pairs = [(_THROUGHPUT, "building_", "_throughput_add",
                  {"synthetics_plant_coal"}, "building")]
        for name in ("building_synthetics_plant_coal_throughput_add",
                     "building_angkor_wat_throughput_add", "foo_add"):
            with self.subTest(name=name):
                status, _info = mss._classify_modifier_name(
                    name, {"building_angkor_wat_throughput_add"}, pairs)
                self.assertIn(status, ("unknown", "suspicious"))
        self.assertEqual(
            mss._classify_modifier_name(
                "building_synthetics_plant_biomass_throughput_add", set(), pairs),
            ("engine", {}),
        )


# The scripted effects #1403 quotes from the 1.15 tree's report, each as the
# parser hands it over: called `name = yes` inside an effect block.
_ISSUE_1403_EFFECTS = (
    "te_demog_cause_deaths_country_add",
    "un_veto_record_add",
    "covert_counterintel_alert_add",
)


def _build_scripted_call_fixture():
    """A mod whose scripted effects and triggers have modifier-shaped names.

    Values are the parser's `('=', value)` tuples, as in the real tree."""
    effects = {
        "te_demog_cause_deaths_country_add": {"change_variable": ("=", {"name": ("=", "x")})},
        "un_veto_record_add": {"change_variable": ("=", {"name": ("=", "y")})},
        "covert_counterintel_alert_add": {"add_modifier": ("=", {"name": ("=", "z")})},
        "nd_log_doctrine_set": {"debug_log": ("=", "x")},
        "foo_shared_add": {"debug_log": ("=", "x")},
        # The callers.
        "te_demog_country_census": {
            "every_scope_state": ("=", {"te_demog_cause_deaths_country_add": ("=", "yes")}),
        },
        "un_vote_cast_veto": {
            "if": ("=", {"else": ("=", {"custom_tooltip": ("=", {
                "un_veto_record_add": ("=", "yes"),
            })})}),
        },
        "nd_set_doctrine": {"nd_log_doctrine_set": ("=", "yes")},
    }
    triggers = {
        "foo_can_set": {"always": ("=", "yes")},
        "foo_caller": {"NOT": ("=", {"foo_can_set": ("=", "no")})},
    }
    events = {
        "covert_warfare.5": {
            "option": ("=", {"covert_counterintel_alert_add": ("=", "yes")}),
        },
    }
    sguis = {
        "foo_sgui": {"is_valid": ("=", {"foo_can_set": ("=", "yes")})},
    }
    pms = {
        "pm_test": {
            "country_modifiers": ("=", {"unscaled": ("=", {
                # Shares a scripted effect's name, but `= 5` is no call.
                "foo_shared_add": ("=", "5"),
                # A typo beside the calls must still be reported.
                "foo_unknown_add": ("=", "3"),
            })}),
        },
    }
    jes = {
        "je_test": {
            "possible": ("=", {"modifier:un_veto_record_add": ("=", "yes")}),
        },
    }
    mod_parsers = {
        "Scripted Effects": _MockParser(effects),
        "Scripted Triggers": _MockParser(triggers),
        "Events": _MockParser(events),
        "Scripted Guis": _MockParser(sguis),
        "Production Methods": _MockParser(pms),
        "Journal Entries": _MockParser(jes),
    }
    fake_ms = _MockModState(
        mod_parsers, modifier_types={}, script_values={},
        scripted_effects=effects, scripted_triggers=triggers,
    )
    return fake_ms, {"modifiers": []}


class ValidatorScriptedCallTests(unittest.TestCase):
    """#1403: a scripted effect or trigger called `name = yes` is not a modifier."""

    def setUp(self):
        self.fake_ms, self.fake_engine_docs = _build_scripted_call_fixture()
        self._patches = [
            patch.object(mss, "ms", self.fake_ms),
            patch.object(mss, "engine_docs", self.fake_engine_docs),
            patch.object(mss, "pattern_catalog", []),
            patch.object(mss, "modifier_to_pattern", {}),
            patch.object(mss, "_vocabulary_index", return_value={}),
        ]
        for p in self._patches:
            p.start()
        self.report = mss._validate_engine_coverage()
        self.unknown = {e["name"]: e for e in self.report["unknown_modifiers"]}

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()

    def test_issue_1403_scripted_effect_calls_not_flagged(self):
        for name in _ISSUE_1403_EFFECTS:
            with self.subTest(name=name):
                used = [u for u in self.unknown.get(name, {}).get("used_in", [])
                        if "modifier:" not in u]
                self.assertEqual(used, [], f"{name} is a scripted effect call")

    def test_set_suffixed_scripted_effect_call_not_flagged(self):
        self.assertNotIn("nd_log_doctrine_set", self.unknown)

    def test_scripted_trigger_calls_not_flagged(self):
        """`foo_can_set = yes` in a scripted GUI and `= no` under NOT."""
        self.assertNotIn("foo_can_set", self.unknown)

    def test_number_under_a_scripted_name_still_flagged(self):
        """`foo_shared_add = 5` in a modifier block is not a call."""
        self.assertIn("foo_shared_add", self.unknown)
        self.assertTrue(any("Production Methods/pm_test" in u
                            for u in self.unknown["foo_shared_add"]["used_in"]))

    def test_modifier_trigger_on_a_scripted_name_still_flagged(self):
        """`modifier:NAME` reads a modifier whatever else carries the name."""
        used = self.unknown.get("un_veto_record_add", {}).get("used_in", [])
        self.assertEqual(len(used), 1, used)
        self.assertIn("modifier:un_veto_record_add", used[0])

    def test_real_unknown_beside_the_calls_still_flagged(self):
        self.assertIn("foo_unknown_add", self.unknown)

    def test_nothing_suspicious(self):
        self.assertEqual(self.report["suspicious_modifiers"], [])


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
